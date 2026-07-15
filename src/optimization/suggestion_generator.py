"""
Step 4: 优化建议生成器 — 根据匹配结果生成简历修改建议
使用 LLM 生成按段落分类的具体优化建议，带输出校验
"""

import json
import logging
from typing import List

from langchain_core.messages import HumanMessage, SystemMessage

from src.generation.llm import get_llm
from src.generation.llm_schemas import SuggestionResult
from src.generation.output_validator import LLMOutputError, parse_and_validate

logger = logging.getLogger("suggestion_generator")

SUGGESTION_PROMPT = """你是一位资深简历优化顾问，拥有10年以上的技术招聘和简历润色经验。
你的任务是分析候选人简历与目标岗位的差距，生成具体、可操作的优化建议。

请以 JSON 格式返回：
{
  "suggestions": [
    {
      "section": "summary/experience/skills/education/projects/format",
      "severity": "critical/recommended/optional",
      "original": "原文片段（如有）",
      "suggestion": "具体修改建议（包含修改后的示例文本）",
      "reason": "修改原因（结合JD要求说明）"
    }
  ],
  "overall_advice": "整体建议（1-2句话总结最重要的改进方向）"
}

优化原则：
1. **STAR法则**：每条经历应包含 Situation → Task → Action → Result
2. **量化成就**：增加具体数字（提升X%、节省Y时间、处理Z数据量）
3. **动作动词**：使用强有力的动词开头（设计、实现、主导、优化、构建）
4. **关键词匹配**：自然融入JD中的关键词，但不要堆砌
5. **ATS友好**：使用标准标题、避免表格图片、控制长度为1-2页
6. **诚实原则**：只建议在真实经历基础上优化表述，不编造经历

severity 标准：
- critical: 严重影响匹配度（如缺少JD要求的核心技能描述）
- recommended: 建议优化（如经历描述不够量化、缺少关键词）
- optional: 锦上添花（如格式美化、增加项目细节）

只返回 JSON，不要其他文字。"""


def generate_suggestions(
    jd_summary: str,
    jd_skills: List[dict],
    resume_sections: dict[str, str],
    match_results: List[dict],
) -> dict:
    """
    生成简历优化建议

    Args:
        jd_summary: JD 摘要
        jd_skills: JD 技能列表
        resume_sections: 简历各段落
        match_results: 技能匹配结果

    Returns:
        {
            "suggestions": list[dict],
            "overall_advice": str
        }
    """
    llm = get_llm(temperature=0.3)

    # 提取缺失和部分匹配的技能
    gap_skills = [
        r for r in match_results
        if r.get("status") in ("missing", "partial_match")
    ]
    matched_skills = [r for r in match_results if r.get("status") == "match"]

    gap_text = "\n".join([
        f"- [{r['status']}] {r['skill']}: {r.get('detail', '')}"
        for r in gap_skills
    ]) if gap_skills else "无明显技能差距"

    matched_text = ", ".join([r["skill"] for r in matched_skills]) if matched_skills else "无"

    # 构建简历完整视图
    resume_full = "\n\n".join([
        f"### {section.upper()}\n{content}"
        for section, content in resume_sections.items()
        if content
    ])

    prompt = f"""请分析以下信息并生成优化建议：

【目标岗位概述】
{jd_summary}

【JD 要求技能】
{json.dumps(jd_skills, ensure_ascii=False, indent=2)[:1000]}

【已匹配技能】
{matched_text}

【技能差距】
{gap_text}

【当前简历】
{resume_full[:3000]}

请按照系统提示中的 JSON 格式生成优化建议。"""

    messages = [
        SystemMessage(content=SUGGESTION_PROMPT),
        HumanMessage(content=prompt),
    ]

    response = llm.invoke(messages)
    content = response.content.strip()

    try:
        validated = parse_and_validate(
            content,
            SuggestionResult,
            context="优化建议",
        )
    except LLMOutputError:
        logger.warning("优化建议 JSON 解析失败，使用 temperature=0 重试...")
        llm_retry = get_llm(temperature=0)
        response_retry = llm_retry.invoke(messages)
        validated = parse_and_validate(
            response_retry.content.strip(),
            SuggestionResult,
            context="优化建议（重试）",
        )

    return validated.model_dump()
