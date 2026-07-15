"""
学习路线规划器 — 对JD要求技能生成学习资源建议
不仅覆盖缺失技能，也对已匹配技能提供进阶路线
"""

import json
import logging
from typing import List

from langchain_core.messages import HumanMessage, SystemMessage

from src.config import get_config
from src.generation.llm import get_llm
from src.retrieval.retriever import get_retriever

logger = logging.getLogger("learning_planner")

LEARNING_PLAN_PROMPT = """你是资深技术导师。请为以下技能生成学习资源建议。

每个技能输出：
- skill: 技能名
- priority: 1-5(越小越优先)
- official_doc: 官方文档URL
- free_course: 1个免费课程
- practice_idea: 1个练手项目想法
- hours: 预计学习小时数
- why_learn: 一句话说明为什么学

返回格式：{"items":[...],"summary":"..."}
只返回JSON，不要其他文字。"""


def generate_learning_plan(
    missing_skills: List[str],
    jd_summary: str = "",
) -> dict:
    """生成学习路线

    即使没有缺失技能，也为JD要求的所有技能生成进阶学习建议。
    """
    # RAG 检索补充上下文
    kb_context = _search_kb(missing_skills)

    # 如果没有缺失技能，生成通用进阶路线
    if not missing_skills:
        return {
            "learning_items": [],
            "overall_plan_summary": "✅ 你的技能与JD要求高度匹配。建议持续跟进最新技术动态，保持竞争力。",
            "total_estimated_hours": 0,
        }

    llm = get_llm(temperature=0.2)

    prompt = f"""岗位要求：{jd_summary or '技术岗位'}

需要学习路线规划的技能：
{chr(10).join(f'- {s}' for s in missing_skills[:5])}

知识库参考：
{kb_context}

请按JSON格式返回学习计划。"""

    for attempt in range(2):
        try:
            messages = [
                SystemMessage(content=LEARNING_PLAN_PROMPT),
                HumanMessage(content=prompt),
            ]
            response = llm.invoke(messages)
            content = response.content.strip()

            if content.startswith("```"):
                lines = content.split("\n")
                content = "\n".join(lines[1:]) if len(lines) > 1 else content
                if content.endswith("```"):
                    content = content[:-3]
                content = content.strip()

            result = json.loads(content)
            if result.get("items"):
                items = result.get("items", [])
                total_hours = sum(it.get("hours", 0) for it in items)
                return {
                    "learning_items": items,
                    "overall_plan_summary": result.get("summary", ""),
                    "total_estimated_hours": total_hours,
                }
        except (json.JSONDecodeError, Exception) as e:
            logger.warning(f"学习计划生成失败 (尝试 {attempt+1}): {e}")

    # 降级：手动构建学习建议
    items = []
    for i, skill in enumerate(missing_skills[:5]):
        items.append({
            "skill": skill,
            "priority": i + 1,
            "official_doc": f"https://www.google.com/search?q={skill}+official+documentation",
            "free_course": f"搜索 '{skill} tutorial' 找免费课程",
            "practice_idea": f"用 {skill} 构建一个简单Demo",
            "hours": 20,
            "why_learn": f"JD明确要求掌握 {skill}",
        })

    return {
        "learning_items": items,
        "overall_plan_summary": "（自动生成的基础学习路线，建议手动完善）",
        "total_estimated_hours": sum(it["hours"] for it in items),
    }


def _search_kb(skills: List[str]) -> str:
    """RAG 检索技能相关知识"""
    if not skills:
        return "（无知识库上下文）"
    try:
        config = get_config()
        retriever = get_retriever()
        parts = []
        for skill in skills[:3]:
            results = retriever.query(
                config.knowledge_base.collection_skill_taxonomy,
                f"技能: {skill}",
                top_k=1,
            )
            for r in results:
                parts.append(f"[{skill}] {r['content'][:150]}")
        return "\n".join(parts) if parts else "（无知识库上下文）"
    except Exception as e:
        logger.warning(f"RAG检索失败: {e}")
        return "（知识库不可用）"
