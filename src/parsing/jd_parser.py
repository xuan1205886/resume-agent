"""
Step 1: JD 解析器 — 从职位描述中提取结构化技能和需求
使用 LLM 进行结构化信息提取，带输出校验
"""

import json
import logging
from typing import List

from langchain_core.messages import HumanMessage, SystemMessage

from src.generation.llm import get_llm
from src.generation.llm_schemas import JDParseResult
from src.generation.output_validator import LLMOutputError, parse_and_validate

logger = logging.getLogger("jd_parser")

JD_PARSE_PROMPT = """你是一位资深技术招聘专家。请分析以下职位描述(JD)，提取结构化信息。

请以 JSON 格式返回，包含以下字段：
{
  "position": "岗位名称",
  "company": "公司名称（如果有）",
  "summary": "岗位概述（1-2句话）",
  "responsibilities": ["职责1", "职责2", ...],
  "skills": [
    {
      "name": "技能名",
      "category": "hard/soft/tool/domain",
      "proficiency": "required/preferred/nice-to-have",
      "description": "JD中对该技能的描述"
    }
  ],
  "education": "学历要求",
  "experience_years": "经验年限要求",
  "other_requirements": ["其他要求"]
}

注意：
1. 硬技能(hard)：编程语言、框架、数据库等技术技能
2. 软技能(soft)：沟通、领导力、团队协作等
3. 工具(tool)：Docker、Git、JIRA等工具
4. 领域(domain)：行业特定知识（金融、医疗等）
5. proficiency 根据 JD 措辞判断：明确要求的为 required，加分项的为 preferred，提到的为 nice-to-have
6. 如果 JD 中没有明确提到的字段，用空字符串或空数组

只返回 JSON，不要其他文字。"""


def parse_jd(jd_text: str) -> dict:
    """
    解析职位描述文本，提取结构化信息

    Args:
        jd_text: 职位描述文本

    Returns:
        结构化的 JD 信息字典

    Raises:
        LLMOutputError: LLM 返回无法解析
        ValueError: 输入为空
    """
    if not jd_text or not jd_text.strip():
        raise ValueError("JD 文本为空，无法解析")

    llm = get_llm(temperature=0.1)

    messages = [
        SystemMessage(content=JD_PARSE_PROMPT),
        HumanMessage(content=f"请分析以下职位描述：\n\n{jd_text[:4000]}"),
    ]

    response = llm.invoke(messages)
    content = response.content.strip()

    try:
        validated = parse_and_validate(
            content,
            JDParseResult,
            context="JD 解析",
        )
    except LLMOutputError:
        # 重试一次：使用更低温度
        logger.warning("JD 解析 JSON 失败，使用 temperature=0 重试...")
        llm_retry = get_llm(temperature=0)
        response_retry = llm_retry.invoke(messages)
        validated = parse_and_validate(
            response_retry.content.strip(),
            JDParseResult,
            context="JD 解析（重试）",
        )

    return validated.model_dump()


def extract_jd_skills_only(jd_text: str) -> List[dict]:
    """仅提取 JD 中的技能列表，不做完整解析"""
    result = parse_jd(jd_text)
    return result.get("skills", [])
