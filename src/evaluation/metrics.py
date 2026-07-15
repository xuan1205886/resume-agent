"""
评估指标计算 — 基于第一性原理的智能评估
不只做逐字匹配，而是分析系统行为质量
"""

from typing import List


def compute_evaluation_metrics(
    jd_skills: List[dict],
    match_results: List[dict],
    parsed_resume: dict,
    fact_check: dict,
    optimized_resume_md: str,
) -> dict:
    """计算 4 维评估指标 + 智能 Badcase

    指标含义：
    - jd_coverage: JD要求技能中，简历能覆盖的比例（只算 match + partial_match×0.5）
    - match_quality: 匹配结果的置信度（有detail分析的 match 才算高质量）
    - fact_trust: 事实核查通过率（无漂移+轻微漂移 / 总数）
    - format_score: 输出简历的格式完整度

    Badcase 不是"缺失技能列表"（那是正常分析结果），而是：
    1. 事实虚构：生成的简历编造了原文没有的内容（fact_check.fabricated）
    2. 严重漂移：修改了原文的关键事实（fact_check.major）
    3. 匹配矛盾：简历明确有某技能但系统判定为 missing（假阴性）
    4. 低质量匹配：判定为 match 但没有具体证据支撑
    """
    # === 1. JD 覆盖率 ===
    total_jd = len(jd_skills)
    if total_jd == 0:
        jd_coverage = 0.0
    else:
        matched = sum(1 for r in match_results if r.get("status") == "match")
        partial = sum(1 for r in match_results if r.get("status") == "partial_match")
        jd_coverage = (matched + partial * 0.5) / total_jd

    # === 2. 匹配质量 ===
    # 有 detail 且长度 >20 字符的 match 才算高质量
    all_matches = [r for r in match_results if r.get("status") in ("match", "partial_match")]
    if all_matches:
        quality_matches = sum(
            1 for r in all_matches
            if len(r.get("detail", "")) > 20
        )
        match_quality = quality_matches / len(all_matches)
    else:
        match_quality = 0.0

    # === 3. 事实可信度 ===
    verdicts = fact_check.get("verdicts", [])
    if verdicts:
        trustworthy = sum(
            1 for v in verdicts
            if v.get("drift_level") in ("none", "minor")
        )
        fact_trust = trustworthy / len(verdicts)
    else:
        fact_trust = 0.0  # 无核查数据，不可信

    # === 4. 格式完整度 ===
    required_sections = ["summary", "skills", "experience", "education"]
    if optimized_resume_md:
        md_lower = optimized_resume_md.lower()
        found = sum(1 for s in required_sections if s in md_lower)
        format_score = found / len(required_sections)
    else:
        format_score = 0.0

    # === 智能 Badcase 分析 ===
    badcases = []

    # Type 1: 事实虚构/严重漂移
    for v in verdicts:
        drift = v.get("drift_level", "")
        if drift in ("major", "fabricated"):
            badcases.append({
                "type": f"事实{'虚构' if drift == 'fabricated' else '严重漂移'}",
                "severity": "critical" if drift == "fabricated" else "warning",
                "generated": v.get("generated_text", "")[:150],
                "original": v.get("original_text", "")[:150],
                "explanation": v.get("explanation", ""),
            })

    # Type 2: 匹配矛盾（简历里明显有但判定为缺失）
    resume_skills_text = _get_resume_skills_text(parsed_resume).lower()
    for r in match_results:
        if r.get("status") == "missing":
            skill_name = r.get("skill", "").lower()
            # 检查简历中是否真的提到了这个技能
            if skill_name and len(skill_name) > 2 and skill_name in resume_skills_text:
                badcases.append({
                    "type": "匹配矛盾（假阴性）",
                    "severity": "warning",
                    "skill": r.get("skill", ""),
                    "detail": f"简历中明确提到了 {r.get('skill', '')}，但系统判定为缺失。可能原因：表达方式不标准或上下文不足。",
                })

    # Type 3: 低质量匹配（claim match 但没有证据）
    for r in match_results:
        if r.get("status") == "match" and len(r.get("detail", "")) < 20:
            badcases.append({
                "type": "低质量匹配",
                "severity": "info",
                "skill": r.get("skill", ""),
                "detail": "系统判定为匹配但缺乏具体证据分析。",
            })

    # Type 4: 简历解析质量提示
    resume_skills = parsed_resume.get("skills", [])
    experience = parsed_resume.get("experience", [])
    if not resume_skills and not experience:
        if not parsed_resume:
            badcases.append({
                "type": "简历数据未传入",
                "severity": "info",
                "detail": "Evaluation 页面未收到解析后的简历数据。这不影响优化结果，仅影响此页面的指标计算。",
            })
        else:
            badcases.append({
                "type": "简历解析不完整",
                "severity": "warning",
                "detail": "未从简历中提取到技能列表或工作经历。如果简历是扫描件，建议使用文字版PDF以获得更好的解析效果。",
            })
    elif not resume_skills:
        badcases.append({
            "type": "技能提取不完整",
            "severity": "info",
            "detail": "简历解析未提取到独立技能列表，技能可能散落在经历描述中，不影响匹配分析。",
        })

    return {
        "jd_coverage": round(jd_coverage, 2),
        "match_quality": round(match_quality, 2),
        "fact_trust": round(fact_trust, 2),
        "format_score": round(format_score, 2),
        "badcases": badcases[:15],  # 最多15条
    }


def _get_resume_skills_text(parsed_resume: dict) -> str:
    """从解析后的简历中提取所有技能相关文本"""
    parts = []
    skills = parsed_resume.get("skills", [])
    if isinstance(skills, list):
        parts.extend(skills)
    for exp in parsed_resume.get("experience", []):
        if isinstance(exp, dict):
            parts.extend(exp.get("bullets", []))
    for proj in parsed_resume.get("projects", []):
        if isinstance(proj, dict):
            parts.append(proj.get("tech_stack", ""))
            parts.extend(proj.get("bullets", []))
    return " ".join(str(p) for p in parts if p)
