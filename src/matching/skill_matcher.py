"""
Step 3: 技能匹配器 — RAG 检索 + LLM 差距分析
对比 JD 需求与简历技能，找出匹配/部分匹配/缺失项
带输出校验和 Reranker 精排
"""

import logging
from typing import List

from langchain_core.messages import HumanMessage, SystemMessage

from src.config import get_config
from src.generation.llm import get_llm
from src.generation.llm_schemas import MatchAnalysisResult
from src.generation.output_validator import LLMOutputError, parse_and_validate
from src.retrieval.retriever import get_retriever
from src.retrieval.reranker import get_reranker

logger = logging.getLogger("skill_matcher")

MATCH_ANALYSIS_PROMPT = """你是一位资深技术招聘专家。请对比 JD 要求的技能和候选人简历中实际展示的技能，进行匹配分析。

请以 JSON 格式返回：
{
  "match_results": [
    {
      "skill": "技能名",
      "status": "match/partial_match/missing/mismatch",
      "score": 0.0-1.0,
      "detail": "详细分析（为什么匹配/不匹配）"
    }
  ],
  "match_summary": "整体匹配概述（2-3句话）",
  "overall_score": 0.0-1.0
}

判断标准：
- match: 简历中明确展示，有具体项目或经验支撑，且与JD要求匹配
- partial_match: 简历中有提到但不够深入，或JD中为preferred要求
- missing: JD要求的技能在简历中完全没有体现
- mismatch: 简历技能与JD方向不匹配（如JD要求后端，简历全是前端）

只返回 JSON，不要其他文字。"""


def match_skills(
    jd_skills: List[dict],
    resume_sections: dict[str, str],
    jd_summary: str = "",
) -> dict:
    """
    执行技能匹配分析

    流程：
    1. RAG 检索：在知识库中查找 JD 所需技能的上下文信息
    2. Reranker 精排
    3. LLM 综合分析：对比 JD 和简历

    Args:
        jd_skills: JD 提取的技能列表
        resume_sections: 简历各段落文本
        jd_summary: JD 摘要

    Returns:
        {
            "match_results": list[dict],
            "match_summary": str,
            "overall_score": float,
            "kb_context": str
        }
    """
    config = get_config()
    retriever = get_retriever()

    # 1. RAG 检索：在技能分类知识库中搜索 JD 技能上下文
    jd_skill_names = [s.get("name", "") for s in jd_skills if s.get("name", "").strip()]
    if not jd_skill_names:
        return {
            "match_results": [],
            "match_summary": "JD 技能列表为空，无法进行匹配",
            "overall_score": 0.0,
            "kb_context": "",
        }

    query = f"岗位技能要求: {', '.join(jd_skill_names[:15])}"
    if jd_summary:
        query = f"岗位: {jd_summary}\n{query}"

    # 检索技能分类知识库
    kb_results = retriever.query(
        config.knowledge_base.collection_skill_taxonomy,
        query,
        top_k=5,
    )

    # 检索最佳实践知识库
    practice_results = retriever.query(
        config.knowledge_base.collection_best_practices,
        query,
        top_k=3,
    )

    # 2. Reranker 精排：对检索结果重新排序，提高相关性
    all_retrieved = kb_results + practice_results
    if all_retrieved:
        try:
            reranker = get_reranker()
            all_retrieved = reranker.rerank_results(query, all_retrieved)
            logger.debug(f"Reranker 精排完成，共 {len(all_retrieved)} 条结果")
        except Exception as e:
            logger.warning(f"Reranker 精排失败（降级使用原始排序）: {e}")

    # 3. 合并知识库上下文
    kb_context_parts = []
    for r in all_retrieved[:8]:  # 取精排后的前8条
        meta_key = r["metadata"].get("skill_name") or r["metadata"].get("topic") or ""
        kb_context_parts.append(f"[{meta_key}] {r['content'][:300]}")

    kb_context = "\n---\n".join(kb_context_parts) if kb_context_parts else "（无知识库上下文）"

    # 4. LLM 匹配分析
    llm = get_llm(temperature=0.1)

    # 构建简历摘要
    resume_text = f"""
    【简历摘要】{resume_sections.get('summary', '无')}
    【技能】{resume_sections.get('skills', '无')}
    【工作经历】{resume_sections.get('experience', '无')[:1000]}
    【项目经历】{resume_sections.get('projects', '无')[:800]}
    【教育】{resume_sections.get('education', '无')}
    """

    # 构建 JD 技能要求
    jd_skills_text = "\n".join([
        f"- [{s.get('category', '')}] {s.get('name', '')} ({s.get('proficiency', '')}): {s.get('description', '')}"
        for s in jd_skills
    ])

    prompt = f"""请分析以下 JD 技能要求与候选人简历的匹配情况：

【JD 技能要求】
{jd_skills_text}

【候选人简历】
{resume_text}

【知识库参考（技能分类和最佳实践）】
{kb_context}

请按照系统提示中的 JSON 格式返回匹配分析结果。"""

    messages = [
        SystemMessage(content=MATCH_ANALYSIS_PROMPT),
        HumanMessage(content=prompt),
    ]

    response = llm.invoke(messages)
    content = response.content.strip()

    try:
        validated = parse_and_validate(
            content,
            MatchAnalysisResult,
            context="技能匹配",
        )
    except LLMOutputError:
        logger.warning("技能匹配 JSON 解析失败，使用 temperature=0 重试...")
        llm_retry = get_llm(temperature=0)
        response_retry = llm_retry.invoke(messages)
        validated = parse_and_validate(
            response_retry.content.strip(),
            MatchAnalysisResult,
            context="技能匹配（重试）",
        )

    result = validated.model_dump()
    result["kb_context"] = kb_context
    return result
