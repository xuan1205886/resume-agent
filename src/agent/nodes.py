"""
Multi-Agent 节点实现 — 6 个 Agent，各自负责一个职责

每个 Agent 通过 Tool Calling 调用底层 Tool：
  Agent 1: JD Analyzer     — JDParserTool
  Agent 2: Resume Parser    — ResumeParserTool
  Agent 3: Skill Matcher    — SkillMatchTool
  Agent 4: Resume Optimizer — BulletScoreTool + FactCheckTool
  Agent 5: Interview Generator — InterviewGenTool
  Agent 6: Learning Planner — LLM 直接生成学习路线
"""

import json
import logging
from typing import Any, Dict

from src.agent.state import AgentState
from src.agent.tools import (
    JDParserTool,
    ResumeParserTool,
    SkillMatchTool,
    BulletScoreTool,
    FactCheckTool,
)
from src.parsing.resume_parser import extract_text_from_pdf
from src.optimization.resume_writer import _assemble_resume, _assemble_with_suggestions, _fallback_full_rewrite
from src.optimization.suggestion_generator import generate_suggestions
from src.config import get_config

logger = logging.getLogger("agent_nodes")


def _skipped(step: int, name: str, reason: str) -> Dict[str, Any]:
    """上游 Agent 失败时，返回 skipped 状态而非静默崩溃"""
    logger.warning(f"[Agent {step}/6] {name} 跳过: {reason}")
    return {
        "error": "",
        "_skipped": True, "_skip_reason": reason,
    }

# ===== Agent 1: JD Analyzer =====

def node_jd_analyzer(state: AgentState) -> Dict[str, Any]:
    """Agent 1: JD Analyzer — 使用 JDParserTool 解析职位描述"""
    logger.info("[Agent 1/6] JD Analyzer 调用 parse_job_description tool...")
    try:
        jd_text = state.get("jd_text", "")
        if not jd_text.strip():
            return {"error": "JD 文本为空"}

        tool = JDParserTool()
        result = tool._run(jd_text=jd_text)

        return {
            "jd_parsed": result,
            "jd_skills": result.get("skills", []),
            "jd_summary": result.get("summary", ""),
            "jd_position": result.get("position", ""),
            "error": "",
        }
    except Exception as e:
        logger.error(f"JD Analyzer 失败: {e}")
        return _skipped(1, "JD Analyzer", str(e))


# ===== Agent 2: Resume Parser =====

def node_resume_parser(state: AgentState) -> Dict[str, Any]:
    """Agent 2: Resume Parser — 使用 ResumeParserTool 解析简历PDF"""
    logger.info("[Agent 2/6] Resume Parser 调用 parse_resume tool...")
    try:
        resume_text = state.get("resume_text", "")
        pdf_path = state.get("resume_pdf_path", "")

        if resume_text.strip():
            # 已有文本，直接用 tool 结构化
            from src.parsing.resume_parser import structure_resume, build_resume_sections
            parsed = structure_resume(resume_text)
            sections = build_resume_sections(parsed)
            result = {"parsed": parsed, "sections": sections, "raw_length": len(resume_text)}
        elif pdf_path:
            tool = ResumeParserTool()
            result = tool._run(pdf_path=pdf_path)
        else:
            return {"error": "简历文本为空且无PDF路径"}

        return {
            "parsed_resume": result.get("parsed", {}),
            "resume_sections": result.get("sections", {}),
            "resume_text": resume_text or "",
            "error": "",
        }
    except Exception as e:
        logger.error(f"Resume Parser 失败: {e}")
        return _skipped(2, "Resume Parser", str(e))


# ===== Agent 3: Skill Matcher =====

def node_skill_matcher(state: AgentState) -> Dict[str, Any]:
    """Agent 3: Skill Matcher — 使用 SkillMatchTool 进行技能匹配"""
    logger.info("[Agent 3/6] Skill Matcher 调用 match_skills tool...")
    try:
        jd_skills = state.get("jd_skills", [])
        resume_sections = state.get("resume_sections", {})

        if not jd_skills:
            return {"error": "JD 技能列表为空"}

        tool = SkillMatchTool()
        result = tool._run(
            jd_skills_json=json.dumps(jd_skills, ensure_ascii=False),
            resume_sections_json=json.dumps(resume_sections, ensure_ascii=False),
            jd_summary=state.get("jd_summary", ""),
        )

        missing = [
            {"name": r.get("skill", ""), "status": r.get("status", "")}
            for r in result.get("match_results", [])
            if r.get("status") == "missing"
        ]

        return {
            "match_results": result.get("match_results", []),
            "match_summary": result.get("match_summary", ""),
            "overall_score": result.get("overall_score", 0.0),
            "missing_skills": missing,
            "error": "",
        }
    except Exception as e:
        logger.error(f"Skill Matcher 失败: {e}")
        return _skipped(3, "Skill Matcher", str(e))


# ===== Agent 4: Resume Optimizer =====

def node_resume_optimizer(state: AgentState) -> Dict[str, Any]:
    """Agent 4: Resume Optimizer — 打分选 bullet + 合并生成建议和简历 + 可选事实核查

    优化后流程（减少 1 次 LLM 调用）：
      4a. 提取 bullet pool（纯代码）
      4b. 规则打分 + LLM 排序验证（智能跳过）
      4c. 一次 LLM 调用同时产出优化建议和简历全文
      4d. 可选：事实核查（通过 config.agent.enable_fact_check 控制）
    """
    logger.info("[Agent 4/6] Resume Optimizer 开始优化...")
    try:
        jd_summary = state.get("jd_summary", "")
        jd_position = state.get("jd_position", "")
        jd_skills = state.get("jd_skills", [])
        resume_sections = state.get("resume_sections", {})
        parsed_resume = state.get("parsed_resume", {})
        match_results = state.get("match_results", [])

        # 4a+4b. 规则打分 + LLM 排序验证（BulletScoreTool._run 内部调用 extract_bullet_pool）
        from src.optimization.bullet_scorer import llm_reorder_bullets
        from src.generation.llm_schemas import BulletScore

        bullet_tool = BulletScoreTool()
        scored_result = bullet_tool._run(
            parsed_resume_json=json.dumps(parsed_resume, ensure_ascii=False),
            jd_skills_json=json.dumps(jd_skills, ensure_ascii=False),
            match_results_json=json.dumps(match_results, ensure_ascii=False),
        )

        if scored_result["total_count"] == 0:
            # 无结构化 bullets，回退到全文本模式
            result = _fallback_full_rewrite(
                jd_summary, jd_position, resume_sections, parsed_resume,
                match_results, [],
            )
            suggestions_list = []
            overall_advice = ""
            fact_check = result.get("fact_check", {})
        else:
            scored_bullets = [BulletScore(**s) for s in scored_result["bullets"]]
            reordered = llm_reorder_bullets(scored_bullets, jd_summary, jd_position)

            # 4c. 合并调用：一次 LLM 产出建议 + 简历（节省 ~5-8s）
            merged = _assemble_with_suggestions(
                reordered, parsed_resume, jd_summary, jd_position,
                match_results, jd_skills,
            )
            optimized_md = merged["optimized_resume_md"]
            suggestions_list = merged["suggestions"]
            overall_advice = merged["overall_advice"]

            # 4d. 可选：事实核查
            cfg = get_config()
            if cfg.agent.enable_fact_check:
                fact_tool = FactCheckTool()
                fact_check = fact_tool._run(
                    optimized_resume_md=optimized_md,
                    scored_bullets_json=json.dumps([s.model_dump() for s in reordered], ensure_ascii=False),
                    parsed_resume_json=json.dumps(parsed_resume, ensure_ascii=False),
                )
            else:
                fact_check = {}

            # 序列化 scored_bullets 供前端审查（仅保留关键字段，避免数据过大）
            scored_bullets_for_frontend = [
                {
                    "id": s.bullet.id,
                    "text": s.bullet.text,
                    "source_type": s.bullet.source_type,
                    "company": s.bullet.company,
                    "title": s.bullet.title,
                    "total_score": s.total_score,
                    "matched_skills": s.matched_skills,
                }
                for s in reordered
            ]

            result = {
                "optimized_resume_md": optimized_md,
                "fact_check": fact_check,
                "selected_bullets_count": len(reordered),
                "total_bullets_count": scored_result["total_count"],
                "scored_bullets": scored_bullets_for_frontend,
            }

        return {
            "suggestions": suggestions_list,
            "overall_advice": overall_advice,
            "optimized_resume_md": result.get("optimized_resume_md", ""),
            "fact_check": result.get("fact_check", {}),
            "selected_bullets_count": result.get("selected_bullets_count", 0),
            "total_bullets_count": result.get("total_bullets_count", 0),
            "scored_bullets": result.get("scored_bullets", []),
            "error": "",
        }
    except Exception as e:
        logger.error(f"Resume Optimizer 失败: {e}")
        return _skipped(4, "Resume Optimizer", str(e))


# (Agent 5 & 6 and their node functions removed — no longer in use)
