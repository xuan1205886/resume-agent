"""
Multi-Agent State — 6 个 Agent 的完整流水线状态
"""

from typing import Annotated, List, TypedDict

from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage


def _reduce_error(current: str, update: str) -> str:
    """合并并行节点的 error 字段：收集所有非空错误，用分号拼接"""
    if not update:
        return current
    if not current:
        return update
    # 多个并行节点都有错误时，全部保留
    return f"{current}; {update}"


class AgentState(TypedDict):
    """6 Agent 流水线状态

    JD Analyzer → Resume Parser → Skill Matcher → Resume Optimizer
        → Interview Generator → Learning Planner
    """

    # === 输入 ===
    jd_text: str
    resume_text: str           # PDF 提取后的原始文本
    resume_pdf_path: str       # PDF 临时文件路径

    # === JD Analyzer Agent ===
    jd_parsed: dict            # JDParseResult
    jd_skills: List[dict]      # 提取的技能列表
    jd_summary: str            # JD 摘要
    jd_position: str           # 岗位名称

    # === Resume Parser Agent ===
    parsed_resume: dict        # ResumeParseResult
    resume_sections: dict      # 展平的段落文本

    # === Skill Matcher Agent ===
    match_results: List[dict]  # 匹配结果
    match_summary: str         # 匹配摘要
    overall_score: float       # 综合匹配分

    # === Resume Optimizer Agent ===
    suggestions: List[dict]     # 优化建议
    overall_advice: str         # 整体建议
    optimized_resume_md: str    # 优化版简历 Markdown
    fact_check: dict            # FactCheckReport
    selected_bullets_count: int
    total_bullets_count: int

    missing_skills: List[dict]       # 缺失技能（Skill Matcher 输出）

    # === 评估指标 ===
    evaluation_metrics: dict         # JD覆盖率、技能准确率等

    # === 控制 ===
    # 使用 reducer 以支持并行节点同时写入（BinaryOperatorAggregate channel）
    error: Annotated[str, _reduce_error]

    # === 消息历史（Tool Calling 用） ===
    messages: Annotated[List[BaseMessage], add_messages]


def create_initial_state(
    jd_text: str = "",
    resume_text: str = "",
    resume_pdf_path: str = "",
) -> AgentState:
    """创建初始状态"""
    return AgentState(
        jd_text=jd_text,
        resume_text=resume_text,
        resume_pdf_path=resume_pdf_path,
        jd_parsed={},
        jd_skills=[],
        jd_summary="",
        jd_position="",
        parsed_resume={},
        resume_sections={},
        match_results=[],
        match_summary="",
        overall_score=0.0,
        suggestions=[],
        overall_advice="",
        optimized_resume_md="",
        fact_check={},
        selected_bullets_count=0,
        total_bullets_count=0,
        missing_skills=[],
        evaluation_metrics={},
        error="",
        messages=[],
    )
