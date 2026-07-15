"""
Fact-Drift 检查器 — 逐条验证生成简历与原始简历的一致性
用 LLM 对比每条 bullet，标记虚构、改写、失真
"""

import logging
from typing import List

from langchain_core.messages import HumanMessage, SystemMessage

from src.generation.llm import get_llm
from src.generation.llm_schemas import (
    BulletItem,
    BulletScore,
    FactCheckReport,
    FactCheckVerdict,
)
from src.generation.output_validator import LLMOutputError, parse_and_validate
from src.optimization.bullet_extractor import get_bullet_context

logger = logging.getLogger("fact_checker")

FACT_CHECK_PROMPT = """你是一位严谨的简历审计专家。你的任务是逐条对比优化版简历的 bullet 和原始简历的 bullet，检查是否存在事实漂移（fact drift）。

对于每条生成的内容，对照原始 bullet，判断漂移等级：

- **none**（无漂移）：事实完全一致，仅措辞或排版变化。例如"开发了RAG系统" → "主导设计并实现RAG系统"（动词优化，核心事实不变）
- **minor**（轻微漂移）：轻度改写，不影响真实性。例如补充了上下文、调整了语序、合并了多条 bullet 的信息。
- **major**（严重漂移）：新增了原文中没有的技术名词、工具、量化数据，或省略了原文中的重要事实。
- **fabricated**（虚构）：与原文完全不符，找不到任何依据。

特别警惕以下情况（标记为 major 或 fabricated）：
1. 原文没有提到的技术/工具，生成了（如原文没有说用了 Docker，但生成了 "使用 Docker 部署"）
2. 原文没有的量化数字，生成了（如原文只说"优化系统"，生成了"优化系统性能提升30%"）
3. 改变了公司名称、职位、时间
4. 凭空编造了新的项目或经历

请以 JSON 格式返回完整的事实核查报告。只返回 JSON。"""


def run_fact_check(
    optimized_resume_md: str,
    scored_bullets: List[BulletScore],
    parsed_resume: dict,
) -> FactCheckReport:
    """对优化版简历进行事实漂移检查

    流程：
    1. 从优化版简历中提取 experience/projects 部分的 bullets
    2. 逐条与原始 bullet pool 对比
    3. LLM 判断漂移等级

    Args:
        optimized_resume_md: 优化后的 Markdown 简历全文
        scored_bullets: 被选中用于组装的原始 bullets（带评分）
        parsed_resume: 完整的原始简历数据

    Returns:
        FactCheckReport 包含每条 bullet 的核查结论
    """
    if not scored_bullets:
        return FactCheckReport(
            verdicts=[],
            overall_trust_score=-1.0,  # -1 表示"未核查"（前端应显示 N/A 而非 100%）
            summary="无语料可供核查（原始简历无结构化 bullet 或未被选中）",
        )

    llm = get_llm(temperature=0.0, max_tokens=4096)  # 10条verdict每条约400-500 token，总量3000-5000

    # 构建原始 bullet 清单
    original_lines = []
    for s in scored_bullets:
        ctx = get_bullet_context(s.bullet)
        original_lines.append(
            f"ID: {s.bullet.id}\n"
            f"  来源: {ctx}\n"
            f"  原文: {s.bullet.text}\n"
        )

    # 截取简历中 experience 和 projects 部分
    resume_excerpt = _extract_experience_section(optimized_resume_md)

    prompt = f"""请对以下优化后的简历进行事实核查。

【原始简历 Bullets（事实依据）】
{chr(10).join(original_lines)}

【优化后简历（Experience / Projects 部分）】
{resume_excerpt[:3000]}

请逐条对比优化后的 bullet 和原始 bullet，以 JSON 格式返回：

{{
  "verdicts": [
    {{
      "generated_text": "优化后的 bullet 文本",
      "original_text": "对应的原始 bullet 文本（最相似的那条）",
      "drift_level": "none/minor/major/fabricated",
      "explanation": "判断理由",
      "added_facts": ["新增的事实1"],
      "missing_facts": ["丢失的事实1"]
    }}
  ],
  "overall_trust_score": 0.0-1.0,
  "summary": "整体核查结论（1-2句话）"
}}

注意：
1. overall_trust_score 计算方法：每条 major 扣 0.2，每条 fabricated 扣 0.4，最低为 0
2. 如果优化后的 bullet 无法对应任何原始 bullet，标记为 fabricated
3. 如果优化后简历中没有某个原始 bullet，不算问题（可能是被合理裁剪了）

只返回 JSON。"""

    messages = [
        SystemMessage(content=FACT_CHECK_PROMPT),
        HumanMessage(content=prompt),
    ]

    response = llm.invoke(messages)
    content = response.content.strip()

    try:
        report = parse_and_validate(content, FactCheckReport, context="事实核查")
    except LLMOutputError:
        logger.warning("事实核查 JSON 解析失败，使用 temperature=0 重试...")
        llm_retry = get_llm(temperature=0, max_tokens=4096)
        response_retry = llm_retry.invoke(messages)
        report = parse_and_validate(
            response_retry.content.strip(), FactCheckReport, context="事实核查（重试）"
        )

    # 补充统计计数
    report.none_count = sum(1 for v in report.verdicts if v.drift_level == "none")
    report.minor_count = sum(1 for v in report.verdicts if v.drift_level == "minor")
    report.major_count = sum(1 for v in report.verdicts if v.drift_level == "major")
    report.fabricated_count = sum(1 for v in report.verdicts if v.drift_level == "fabricated")

    return report


def _extract_experience_section(markdown_text: str) -> str:
    """从 Markdown 简历中提取 Experience 和 Projects 部分"""
    lines = markdown_text.split("\n")
    in_target = False
    result = []

    for line in lines:
        stripped = line.strip().lower()
        # 检测目标标题
        if stripped.startswith("## ") or stripped.startswith("# "):
            title = stripped.lstrip("#").strip()
            if any(kw in title for kw in ["experience", "工作经历", "项目", "projects"]):
                in_target = True
                result.append(line)
                continue
            elif in_target:
                in_target = False

        if in_target:
            result.append(line)

    return "\n".join(result) if result else markdown_text[:3000]
