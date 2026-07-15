"""
Step 2: 简历解析器 — 从 PDF 简历中提取结构化段落
PyMuPDF 提取文本 + LLM 结构化分节，带输出校验
"""

import logging
import os
from typing import Optional

import fitz  # PyMuPDF
from langchain_core.messages import HumanMessage, SystemMessage

from src.config import get_config
from src.generation.llm import get_llm
from src.generation.llm_schemas import ResumeParseResult
from src.generation.output_validator import LLMOutputError, parse_and_validate

logger = logging.getLogger("resume_parser")

RESUME_PARSE_PROMPT = """你是一位专业的简历解析专家。请将以下从PDF提取的简历文本解析为结构化段落。

请以 JSON 格式返回，包含以下字段：
{
  "contact": {
    "name": "姓名",
    "email": "邮箱",
    "phone": "电话",
    "location": "城市",
    "github": "GitHub链接（如果有）",
    "linkedin": "LinkedIn链接（如果有）"
  },
  "summary": "个人概述（原文）",
  "skills": ["技能1", "技能2", ...],
  "experience": [
    {
      "company": "公司名",
      "title": "职位",
      "duration": "时间段",
      "bullets": ["工作内容1", "工作内容2", ...]
    }
  ],
  "education": [
    {
      "school": "学校",
      "degree": "学位",
      "major": "专业",
      "duration": "时间段"
    }
  ],
  "projects": [
    {
      "name": "项目名",
      "tech_stack": "技术栈",
      "bullets": ["项目描述1", "项目描述2", ...]
    }
  ]
}

注意：
1. 只提取原文中实际存在的信息，不要编造
2. 没有的字段用空字符串或空数组
3. 保持原文内容不变，不要改写
4. 联系方式中只提取明确标注的信息

只返回 JSON，不要其他文字。"""


def extract_text_from_pdf(file_path: str) -> str:
    """
    使用 PyMuPDF 从 PDF 文件中提取文本

    Args:
        file_path: PDF 文件路径

    Returns:
        提取的文本内容

    Raises:
        FileNotFoundError: 文件不存在
        ValueError: PDF 无法解析或文本过短
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"文件不存在: {file_path}")

    config = get_config()
    max_pages = config.resume.max_pages
    min_length = config.resume.min_text_length

    doc = fitz.open(file_path)
    texts = []

    try:
        for i, page in enumerate(doc):
            if i >= max_pages:
                break
            text = page.get_text()
            if text.strip():
                texts.append(text.strip())
    finally:
        doc.close()

    if not texts:
        raise ValueError(f"PDF 文件中未提取到文本: {file_path}")

    full_text = "\n\n".join(texts)

    if len(full_text) < min_length:
        raise ValueError(
            f"提取的文本过短（{len(full_text)}字符 < {min_length}字符），"
            f"可能是扫描件或不支持的格式"
        )

    return full_text


def structure_resume(raw_text: str) -> dict:
    """
    使用 LLM 将原始简历文本结构化为段落

    Args:
        raw_text: 从 PDF 提取的原始文本

    Returns:
        结构化的简历数据

    Raises:
        LLMOutputError: LLM 返回无法解析
        ValueError: 输入为空
    """
    if not raw_text or not raw_text.strip():
        raise ValueError("简历文本为空，无法解析")

    llm = get_llm(temperature=0.1)

    # 截断过长的文本（简历通常不超过5000字）
    text = raw_text[:5000] if len(raw_text) > 5000 else raw_text

    messages = [
        SystemMessage(content=RESUME_PARSE_PROMPT),
        HumanMessage(content=f"请解析以下简历文本：\n\n{text}"),
    ]

    response = llm.invoke(messages)
    content = response.content.strip()

    try:
        validated = parse_and_validate(
            content,
            ResumeParseResult,
            context="简历解析",
        )
    except LLMOutputError:
        # 重试一次：使用更低温度
        logger.warning("简历解析 JSON 失败，使用 temperature=0 重试...")
        llm_retry = get_llm(temperature=0)
        response_retry = llm_retry.invoke(messages)
        validated = parse_and_validate(
            response_retry.content.strip(),
            ResumeParseResult,
            context="简历解析（重试）",
        )

    return validated.model_dump()


def parse_resume_pdf(file_path: str) -> dict:
    """
    完整的简历 PDF 解析流程：
    1. PyMuPDF 提取文本
    2. LLM 结构化为段落

    Args:
        file_path: PDF 文件路径

    Returns:
        结构化的简历数据
    """
    raw_text = extract_text_from_pdf(file_path)
    structured = structure_resume(raw_text)
    structured["_raw_text"] = raw_text
    return structured


def build_resume_sections(parsed_resume: dict) -> dict[str, str]:
    """
    将结构化简历数据展平为段落文本映射
    用于后续 LLM prompt 构建

    Returns:
        {
            "summary": "摘要文本",
            "experience": "经历文本",
            "skills": "技能文本",
            "education": "教育文本",
            "projects": "项目文本"
        }
    """
    sections = {}

    # 摘要
    sections["summary"] = parsed_resume.get("summary", "")

    # 技能
    skills = parsed_resume.get("skills", [])
    sections["skills"] = ", ".join(skills) if isinstance(skills, list) else str(skills)

    # 工作经历
    exp_parts = []
    for exp in parsed_resume.get("experience", []):
        exp_text = f"{exp.get('title', '')} | {exp.get('company', '')} | {exp.get('duration', '')}\n"
        for bullet in exp.get("bullets", []):
            exp_text += f"  - {bullet}\n"
        exp_parts.append(exp_text)
    sections["experience"] = "\n".join(exp_parts)

    # 教育
    edu_parts = []
    for edu in parsed_resume.get("education", []):
        edu_parts.append(f"{edu.get('school', '')} | {edu.get('degree', '')} | {edu.get('major', '')} | {edu.get('duration', '')}")
    sections["education"] = "\n".join(edu_parts)

    # 项目
    proj_parts = []
    for proj in parsed_resume.get("projects", []):
        proj_text = f"项目: {proj.get('name', '')} | 技术栈: {proj.get('tech_stack', '')}\n"
        for bullet in proj.get("bullets", []):
            proj_text += f"  - {bullet}\n"
        proj_parts.append(proj_text)
    sections["projects"] = "\n".join(proj_parts)

    return sections
