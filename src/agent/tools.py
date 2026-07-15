"""
Agent Tools — 6 个 LangChain Tool，供 Multi-Agent 通过 Function Calling 调用
每个 Tool 封装一个核心功能，LLM Agent 可选择调用哪些工具
"""

from typing import List, Optional, Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from src.parsing.jd_parser import parse_jd
from src.parsing.resume_parser import extract_text_from_pdf, structure_resume, build_resume_sections
from src.matching.skill_matcher import match_skills
from src.optimization.bullet_extractor import extract_bullet_pool
from src.optimization.bullet_scorer import score_bullets
from src.optimization.fact_checker import run_fact_check


# ===== Tool 1: JD Parser Tool =====

class JDParserInput(BaseModel):
    jd_text: str = Field(description="职位描述的完整文本")


class JDParserTool(BaseTool):
    name: str = "parse_job_description"
    description: str = "解析职位描述(JD)，提取结构化信息：岗位名称、所需技能、经验要求、学历要求等。输入为JD纯文本，输出为结构化JSON。"
    args_schema: Type[BaseModel] = JDParserInput

    def _run(self, jd_text: str) -> dict:
        return parse_jd(jd_text)


# ===== Tool 2: Resume Parser Tool =====

class ResumeParserInput(BaseModel):
    pdf_path: str = Field(description="简历 PDF 文件的绝对路径")


class ResumeParserTool(BaseTool):
    name: str = "parse_resume"
    description: str = "解析简历PDF文件，提取结构化信息：联系方式、技能列表、工作经历、项目经历、教育背景等。输入为PDF文件路径，输出为结构化JSON。"
    args_schema: Type[BaseModel] = ResumeParserInput

    def _run(self, pdf_path: str) -> dict:
        raw_text = extract_text_from_pdf(pdf_path)
        parsed = structure_resume(raw_text)
        sections = build_resume_sections(parsed)
        return {
            "parsed": parsed,
            "sections": sections,
            "raw_length": len(raw_text),
        }


# ===== Tool 3: Skill Match Tool =====

class SkillMatchInput(BaseModel):
    jd_skills_json: str = Field(description="JD技能列表的JSON字符串")
    resume_sections_json: str = Field(description="简历段落的JSON字符串")
    jd_summary: str = Field(default="", description="JD摘要（可选）")


class SkillMatchTool(BaseTool):
    name: str = "match_skills"
    description: str = "对比JD技能要求和候选人简历，进行技能匹配分析。返回每个技能的匹配状态（match/partial_match/missing/mismatch）、评分和整体匹配度。"
    args_schema: Type[BaseModel] = SkillMatchInput

    def _run(self, jd_skills_json: str, resume_sections_json: str, jd_summary: str = "") -> dict:
        import json
        jd_skills = json.loads(jd_skills_json)
        resume_sections = json.loads(resume_sections_json)
        return match_skills(jd_skills, resume_sections, jd_summary)


# ===== Tool 4: Bullet Score & Select Tool =====

class BulletScoreInput(BaseModel):
    parsed_resume_json: str = Field(description="解析后的简历JSON字符串")
    jd_skills_json: str = Field(description="JD技能列表的JSON字符串")
    match_results_json: str = Field(description="技能匹配结果的JSON字符串")


class BulletScoreTool(BaseTool):
    name: str = "score_and_select_bullets"
    description: str = "从原始简历中提取所有工作经历和项目bullets，根据JD技能匹配度打分排序，选出最相关的8-12条用于简历组装。"
    args_schema: Type[BaseModel] = BulletScoreInput

    def _run(self, parsed_resume_json: str, jd_skills_json: str, match_results_json: str) -> dict:
        import json
        parsed_resume = json.loads(parsed_resume_json)
        jd_skills = json.loads(jd_skills_json)
        match_results = json.loads(match_results_json)

        bullets = extract_bullet_pool(parsed_resume)
        scored = score_bullets(bullets, jd_skills, match_results)

        return {
            "selected_count": len(scored.bullets),
            "total_count": scored.total_bullets_in_pool,
            "bullets": [s.model_dump() for s in scored.bullets],
        }


# ===== Tool 5: Fact Check Tool =====

class FactCheckInput(BaseModel):
    optimized_resume_md: str = Field(description="优化后的Markdown简历全文")
    scored_bullets_json: str = Field(description="被选中用于组装的原始bullets（JSON）")
    parsed_resume_json: str = Field(description="原始简历的完整结构化数据（JSON）")


class FactCheckTool(BaseTool):
    name: str = "check_fact_drift"
    description: str = "对优化版简历进行事实漂移检查，逐条验证生成内容是否忠实于原始简历。输出每条bullet的漂移等级（none/minor/major/fabricated）和整体可信度评分。"
    args_schema: Type[BaseModel] = FactCheckInput

    def _run(self, optimized_resume_md: str, scored_bullets_json: str, parsed_resume_json: str) -> dict:
        import json
        from src.generation.llm_schemas import BulletScore

        scored_dicts = json.loads(scored_bullets_json)
        scored_bullets = [BulletScore(**s) for s in scored_dicts]
        parsed_resume = json.loads(parsed_resume_json)

        report = run_fact_check(optimized_resume_md, scored_bullets, parsed_resume)
        return report.model_dump()


def get_all_tools() -> List[BaseTool]:
    """获取所有 Agent Tool（从 Registry 动态收集）"""
    from src.agent.registry import AgentRegistry
    tools = []
    seen = set()
    for agent in AgentRegistry.list_all():
        for tool in agent.tools:
            tool_type = type(tool).__name__
            if tool_type not in seen:
                tools.append(tool)
                seen.add(tool_type)
    return tools


def get_tools_for_agent(agent_name: str) -> List[BaseTool]:
    """获取特定 Agent 可用的 Tool 子集（从 Registry 查找）

    每个 Agent 只能看到自己需要的 Tool，避免混淆。
    """
    from src.agent.registry import AgentRegistry
    agent = AgentRegistry.get(agent_name)
    if agent:
        return list(agent.tools)
    return []
