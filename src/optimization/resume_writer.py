"""
Step 5: 简历重写器 — 块级组装 + Fact-Drift 检查

新架构（替换旧的全文本 LLM 重写）：
  5a. extract_bullet_pool()      — 从原始简历提取所有 bullets
  5b. score_and_select_bullets() — 规则打分 + LLM 排序验证
  5c. assemble_resume()          — LLM 受限改写（不能编造事实）
  5d. fact_drift_check()        — 逐条验证生成内容 ↔ 原始内容
"""

import logging
from typing import List

from langchain_core.messages import HumanMessage, SystemMessage

from src.generation.llm import get_llm
from src.generation.llm_schemas import BulletScore, FactCheckReport
from src.optimization.bullet_extractor import extract_bullet_pool, get_bullet_context
from src.optimization.bullet_scorer import DEFAULT_TOP_N, llm_reorder_bullets, score_bullets
from src.optimization.fact_checker import run_fact_check

logger = logging.getLogger("resume_writer")

# 受限改写的系统 prompt（强调事实保留）
ASSEMBLY_PROMPT = """你是一位顶级简历写作专家，专门为技术岗位候选人打造ATS友好、面试率高的简历。

## 核心原则：事实保留优先
- 你只能基于【原始 Bullets】中提供的事实进行润色，**绝对不能编造或添加原文中没有的技术、工具、数字、项目**
- 如果原文没有量化数据，**不要自己编一个数字**（如不要说"提升30%"除非原文明确写了）
- 不要改变公司名称、职位、时间段
- 不要新增原文中没有提到的技能到 Skills 部分

## 润色范围（允许的操作）
1. **STAR 格式改写**：将平淡的描述改写为 Situation-Task-Action-Result 结构
2. **措辞优化**：用更有力的动词开头（设计、实现、主导、优化、构建）
3. **结构调整**：将 Skills 按 Languages / Frameworks / Tools / Platforms 分类
4. **Summary 优化**：基于 bullet 中的事实，提炼 3-4 句话的定位陈述
5. **合理裁剪**：如果某个 bullet 与目标岗位完全无关，可以省略

## 格式规范
- 使用 Markdown 格式
- 标准英文标题：## Summary / ## Skills / ## Experience / ## Education / ## Projects
- 联系方式以 Markdown 格式放在顶部（使用提供的信息，不要编造）
- 统一使用 - 开头的无序列表，每个 bullet 2-3 行
- ATS 友好：不使用表格、不嵌入图片、不使用特殊符号

## Output
直接输出优化后的 Markdown 简历全文，不要 JSON。"""


def write_optimized_resume(
    jd_summary: str,
    jd_position: str,
    resume_sections: dict[str, str],
    parsed_resume: dict,
    match_results: list[dict],
    suggestions: list[dict],
) -> dict:
    """块级组装优化简历 + 事实核查

    新流程：
    1. 从原始简历提取所有 bullet（纯代码）
    2. JD 匹配打分 + LLM 排序验证
    3. LLM 受限改写（只润色，不编造）
    4. Fact-Drift 检查

    Args:
        jd_summary: JD 摘要
        jd_position: 目标岗位名称
        resume_sections: 当前简历段落（备用）
        parsed_resume: 解析后的完整简历数据（用于提取 bullets）
        match_results: 技能匹配结果
        suggestions: 优化建议列表

    Returns:
        {
            "optimized_resume_md": str,
            "fact_check": dict (FactCheckReport),
            "selected_bullets_count": int,
            "total_bullets_count": int,
        }
    """
    # ===== 5a. 提取 Bullet Pool =====
    all_bullets = extract_bullet_pool(parsed_resume)
    logger.info(f"提取到 {len(all_bullets)} 条原始 bullets")

    if not all_bullets:
        # 回退：原始简历没有结构化 bullets，交给 LLM 全文本生成
        logger.warning("未提取到结构化 bullets，回退到 LLM 全文本生成模式")
        return _fallback_full_rewrite(
            jd_summary, jd_position, resume_sections, parsed_resume,
            match_results, suggestions,
        )

    # 获取 JD 技能列表
    jd_skills = _extract_jd_skills(parsed_resume, match_results)

    # ===== 5b. 打分 + 选取 + 排序 =====
    scored = score_bullets(all_bullets, jd_skills, match_results, top_n=DEFAULT_TOP_N)
    logger.info(f"规则打分完成: {len(scored.bullets)} 条入选 (共 {scored.total_bullets_in_pool} 条)")

    # LLM 辅助排序验证
    reordered = llm_reorder_bullets(scored.bullets, jd_summary, jd_position)
    logger.info(f"LLM 排序验证完成: {len(reordered)} 条")

    # ===== 5c. LLM 受限改写 =====
    optimized_md = _assemble_resume(
        reordered, parsed_resume, jd_summary, jd_position,
        match_results, suggestions,
    )

    # ===== 5d. Fact-Drift 检查 =====
    fact_check = run_fact_check(optimized_md, reordered, parsed_resume)
    logger.info(
        f"事实核查完成: trust={fact_check.overall_trust_score:.0%}, "
        f"none={fact_check.none_count}, minor={fact_check.minor_count}, "
        f"major={fact_check.major_count}, fabricated={fact_check.fabricated_count}"
    )

    return {
        "optimized_resume_md": optimized_md,
        "fact_check": fact_check.model_dump(),
        "selected_bullets_count": len(reordered),
        "total_bullets_count": scored.total_bullets_in_pool,
    }


# 合并版 prompt：一次 LLM 调用同时产出优化建议和简历全文
ASSEMBLY_WITH_SUGGESTIONS_PROMPT = """你是一位顶级简历优化顾问兼写作专家。请完成两项任务：

1. 基于技能差距分析，生成 3-6 条具体的优化建议
2. 基于原始 Bullets，生成优化版简历全文

返回 JSON 格式（注意 optimized_resume_md 中的换行用 \\n 转义，双引号用 \\\" 转义）：
{
  "suggestions": [...],
  "overall_advice": "整体建议",
  "optimized_resume_md": "Markdown 简历全文（换行已转义为 \\n）"
}

## 简历写作原则
- **事实保留优先**：只能基于原始 Bullets 润色，不编造技术/工具/数字/项目
- **STAR 法则**：每条经历包含 Situation→Task→Action→Result
- **量化成就**：保留原文中的数字，但不要自己编造
- **动作动词**：用有力动词开头（设计、实现、主导、优化、构建）
- **ATS 友好**：标准 Markdown 标题，无表格图片

## 建议生成原则
- critical: 严重影响匹配度（缺少 JD 核心技能描述）
- recommended: 建议优化（经历描述不够量化、缺少关键词）
- optional: 锦上添花（格式美化、增加项目细节）

只返回 JSON，不要其他文字。"""


def _repair_llm_json(text: str) -> str:
    """正则清洗 LLM 返回的 JSON，移除常见噪音，提高解析成功率

    处理：
    1. Markdown 代码块包装 (```json ... ```)
    2. 前导/后随的非 JSON 文字
    3. 尾部逗号
    4. 单引号 JSON
    """
    import re

    # 1. 移除 markdown 代码块
    text = re.sub(r'^```(?:json)?\s*\n?', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\n?```\s*$', '', text)

    # 2. 提取第一个 { 到最后一个 } 之间的内容
    first_brace = text.find('{')
    last_brace = text.rfind('}')
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        text = text[first_brace:last_brace + 1]

    # 3. 修复尾部逗号
    text = re.sub(r',\s*([}\]])', r'\1', text)

    # 4. 修复明显的单引号 JSON
    if text.count("'") > text.count('"'):
        text = re.sub(r"'([^']*)'", r'"\1"', text)

    return text.strip()


def _assemble_with_suggestions(
    selected_bullets: List[BulletScore],
    parsed_resume: dict,
    jd_summary: str,
    jd_position: str,
    match_results: List[dict],
    jd_skills: List[dict],
) -> dict:
    """一次 LLM 调用同时产出优化建议和简历全文

    合并 generate_suggestions() + _assemble_resume() 为单次调用，
    节省一次 API 往返（~5-8s）。
    """
    import json
    from src.generation.llm_schemas import SuggestionResult
    from src.config import get_config as _get_config

    _cfg = _get_config()
    assembly_tokens = _cfg.llm.agent_max_tokens.resume_assembly
    llm = get_llm(temperature=0.3, max_tokens=assembly_tokens)

    # 构建 bullet 素材
    bullet_material = []
    for i, s in enumerate(selected_bullets, 1):
        ctx = get_bullet_context(s.bullet)
        bullet_material.append(
            f"### Bullet {i}\n"
            f"上下文: {ctx}\n"
            f"原文: {s.bullet.text}\n"
        )

    # 匹配摘要
    match_text = []
    for r in match_results[:10]:
        icon = {"match": "✓", "partial_match": "△", "missing": "✗", "mismatch": "✗"}.get(
            r.get("status", ""), ""
        )
        match_text.append(f"{icon} {r['skill']} ({r.get('status', '')})")

    # 技能差距
    gap_skills = [r for r in match_results if r.get("status") in ("missing", "partial_match")]
    matched_skills = [r for r in match_results if r.get("status") == "match"]
    gap_text = "\n".join([
        f"- [{r['status']}] {r['skill']}: {r.get('detail', '')}"
        for r in gap_skills
    ]) if gap_skills else "无明显技能差距"
    matched_text = ", ".join([r["skill"] for r in matched_skills]) if matched_skills else "无"

    # 联系方式
    contact = parsed_resume.get("contact", {})
    contact_text = f"""
姓名: {contact.get('name', '[姓名]')}
邮箱: {contact.get('email', '[待补充]')}
电话: {contact.get('phone', '[待补充]')}
所在地: {contact.get('location', '[待补充]')}
GitHub: {contact.get('github', '[如有请补充]')}
LinkedIn: {contact.get('linkedin', '[如有请补充]')}
"""

    # 教育
    edu_list = parsed_resume.get("education", [])
    edu_text = "\n".join([
        f"- {e.get('school', '')} | {e.get('degree', '')} | {e.get('major', '')} | {e.get('duration', '')}"
        for e in edu_list
    ]) if edu_list else "（原文无教育信息）"

    # 技能
    skills = parsed_resume.get("skills", [])
    skills_text = ", ".join(skills) if skills else "（原文无技能列表）"

    # JD 技能要求
    jd_skills_text = json.dumps(jd_skills, ensure_ascii=False, indent=2)[:1000]

    prompt = f"""请为「{jd_position}」岗位完成优化建议和简历生成。

【目标岗位】
{jd_summary}

【JD 要求技能】
{jd_skills_text}

【已匹配技能】
{matched_text}

【技能差距】
{gap_text}

【候选人联系方式】
{contact_text}

【候选人技能】
{skills_text}

【教育背景】
{edu_text}

【原始经历 Bullets（润色基础素材，不得编造新事实）】
{chr(10).join(bullet_material)}

请按系统提示的 JSON 格式返回优化建议和简历全文。只返回 JSON。"""

    messages = [
        SystemMessage(content=ASSEMBLY_WITH_SUGGESTIONS_PROMPT),
        HumanMessage(content=prompt),
    ]

    response = llm.invoke(messages)
    content = response.content.strip()
    content_cleaned = _repair_llm_json(content)

    try:
        result = json.loads(content_cleaned)
    except json.JSONDecodeError:
        logger.warning("合并调用 JSON 解析失败，使用 temperature=0 重试...")
        llm_retry = get_llm(temperature=0, max_tokens=assembly_tokens)
        response_retry = llm_retry.invoke(messages)
        content_retry = _repair_llm_json(response_retry.content.strip())
        try:
            result = json.loads(content_retry)
        except json.JSONDecodeError:
            logger.error("合并调用 JSON 解析重试也失败，回退到分别调用")
            # 回退：单独调用组装函数（跳过建议生成）
            optimized_md = _assemble_resume(
                selected_bullets, parsed_resume, jd_summary, jd_position,
                match_results, [],
            )
            return {
                "optimized_resume_md": optimized_md,
                "suggestions": [],
                "overall_advice": "",
            }

    # 校验 suggestions（确保类型安全，防止 LLM 返回非列表值导致崩溃）
    raw_suggestions = result.get("suggestions", [])
    if not isinstance(raw_suggestions, list):
        raw_suggestions = []
    try:
        validated = SuggestionResult(suggestions=raw_suggestions, overall_advice=result.get("overall_advice", ""))
        suggestions = validated.suggestions
        overall_advice = validated.overall_advice
    except Exception:
        suggestions = [s for s in raw_suggestions if isinstance(s, dict) and s.get("suggestion", "").strip()]
        overall_advice = result.get("overall_advice", "")

    optimized_md = result.get("optimized_resume_md", "")
    if not optimized_md:
        # 回退：LLM 没产出简历（可能只输出了 suggestions）
        logger.warning("合并调用未产出简历，回退到单独组装")
        optimized_md = _assemble_resume(
            selected_bullets, parsed_resume, jd_summary, jd_position,
            match_results, suggestions,
        )

    logger.info(
        f"合并调用完成: {len(suggestions)} 条建议, "
        f"简历 {len(optimized_md)} 字符"
    )
    return {
        "optimized_resume_md": optimized_md,
        "suggestions": suggestions,
        "overall_advice": overall_advice,
    }


def _assemble_resume(
    selected_bullets: List[BulletScore],
    parsed_resume: dict,
    jd_summary: str,
    jd_position: str,
    match_results: List[dict],
    suggestions: List[dict],
) -> str:
    """LLM 受限改写：将选中的 bullets 组装为最终简历"""
    llm = get_llm(temperature=0.3, max_tokens=4096)

    # 构建 bullet 素材
    bullet_material = []
    for i, s in enumerate(selected_bullets, 1):
        ctx = get_bullet_context(s.bullet)
        bullet_material.append(
            f"### Bullet {i}\n"
            f"上下文: {ctx}\n"
            f"原文: {s.bullet.text}\n"
        )

    # 构建匹配摘要（告诉 LLM 哪些技能是重点）
    match_text = []
    for r in match_results[:10]:
        icon = {"match": "✓", "partial_match": "△", "missing": "✗", "mismatch": "✗"}.get(
            r.get("status", ""), ""
        )
        match_text.append(f"{icon} {r['skill']} ({r.get('status', '')})")

    # 构建建议摘要
    suggestion_text = []
    for s in suggestions[:5]:
        severity = s.get("severity", "")
        suggestion_text.append(f"[{severity}] {s.get('suggestion', '')}")

    # 联系方式
    contact = parsed_resume.get("contact", {})
    contact_text = f"""
姓名: {contact.get('name', '[姓名]')}
邮箱: {contact.get('email', '[待补充]')}
电话: {contact.get('phone', '[待补充]')}
所在地: {contact.get('location', '[待补充]')}
GitHub: {contact.get('github', '[如有请补充]')}
LinkedIn: {contact.get('linkedin', '[如有请补充]')}
"""

    # 教育
    edu_list = parsed_resume.get("education", [])
    edu_text = "\n".join([
        f"- {e.get('school', '')} | {e.get('degree', '')} | {e.get('major', '')} | {e.get('duration', '')}"
        for e in edu_list
    ]) if edu_list else "（原文无教育信息）"

    # 技能
    skills = parsed_resume.get("skills", [])
    skills_text = ", ".join(skills) if skills else "（原文无技能列表）"

    prompt = f"""请基于以下素材，为「{jd_position}」岗位生成一份优化版简历。

【目标岗位】
{jd_summary}

【技能匹配情况（✓已匹配 / △部分匹配 / ✗缺失）】
{chr(10).join(match_text)}

【优化要点】
{chr(10).join(suggestion_text) if suggestion_text else '无特殊建议'}

【候选人联系方式（直接使用，不要修改）】
{contact_text}

【候选人技能（直接使用，只调整排列顺序）】
{skills_text}

【候选人教育背景（直接使用，不要修改）】
{edu_text}

【原始经历 Bullets（润色的基础素材，不得编造新事实）】
{chr(10).join(bullet_material)}

请按照系统提示中的要求，生成优化后的 Markdown 简历全文。直接输出简历，不要有其他说明文字。"""

    messages = [
        SystemMessage(content=ASSEMBLY_PROMPT),
        HumanMessage(content=prompt),
    ]

    response = llm.invoke(messages)
    content = response.content.strip()

    # 清理可能的 markdown 代码块包装
    if content.startswith("```"):
        lines = content.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        content = "\n".join(lines)

    return content


def _fallback_full_rewrite(
    jd_summary: str,
    jd_position: str,
    resume_sections: dict[str, str],
    parsed_resume: dict,
    match_results: list[dict],
    suggestions: list[dict],
) -> dict:
    """回退方案：原始简历没有结构化 bullets 时，使用全文本 LLM 重写

    保留此路径以兼容 PDF 解析失败的场景
    """
    llm = get_llm(temperature=0.3, max_tokens=4096)

    resume_full = "\n\n".join([
        f"### {section.upper()}\n{content}"
        for section, content in resume_sections.items()
        if content
    ])

    match_text = []
    for r in match_results:
        icon = {"match": "[有]", "partial_match": "[部分]", "missing": "[无]", "mismatch": "[不匹配]"}.get(
            r.get("status", ""), ""
        )
        match_text.append(f"{icon} {r['skill']}: {r.get('detail', '')}")

    suggestion_text = []
    for s in suggestions:
        severity_tag = {"critical": "[严重]", "recommended": "[建议]", "optional": "[可选]"}.get(
            s.get("severity", ""), ""
        )
        suggestion_text.append(
            f"{severity_tag} [{s.get('section', '')}] {s.get('suggestion', '')}"
        )

    contact = parsed_resume.get("contact", {})
    contact_text = f"""
姓名: {contact.get('name', '[姓名]')}
邮箱: {contact.get('email', '[待补充]')}
电话: {contact.get('phone', '[待补充]')}
所在地: {contact.get('location', '[待补充]')}
GitHub: {contact.get('github', '[如有请补充]')}
LinkedIn: {contact.get('linkedin', '[如有请补充]')}
"""

    prompt = f"""请根据以下信息，为「{jd_position}」岗位生成一份优化版简历：

【目标岗位】
{jd_summary}

【技能匹配情况】
{chr(10).join(match_text[:10])}

【优化要点】
{chr(10).join(suggestion_text[:8])}

【候选人联系方式】
{contact_text}

【候选人原始简历】
{resume_full[:3000]}

请生成优化后的 Markdown 简历全文。注意基于原文事实，不要编造经历。"""

    messages = [
        SystemMessage(content=ASSEMBLY_PROMPT),
        HumanMessage(content=prompt),
    ]

    response = llm.invoke(messages)
    content = response.content.strip()

    if content.startswith("```"):
        lines = content.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        content = "\n".join(lines)

    return {
        "optimized_resume_md": content,
        "fact_check": FactCheckReport(
            verdicts=[],
            overall_trust_score=0.0,
            summary="（回退模式：原始简历无结构化 bullets，无法进行事实核查）",
        ).model_dump(),
        "selected_bullets_count": 0,
        "total_bullets_count": 0,
    }


def _extract_jd_skills(parsed_resume: dict, match_results: list[dict]) -> list[dict]:
    """从 match_results 中恢复 JD 技能列表（用于 bullet 打分）

    注意：api_server.py 传的 jd_skills 可能来自 parsed JD，
    但 write_optimized_resume 不再接收 jd_skills 参数。
    这里从 match_results 反向推断 JD 技能。
    """
    skills = []
    for r in match_results:
        skills.append({
            "name": r.get("skill", ""),
            "category": "hard",
            "proficiency": "required" if r.get("status") == "missing" else "preferred",
        })
    return skills
