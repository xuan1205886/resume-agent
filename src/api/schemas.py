"""
Pydantic 请求/响应模型 — 复用 rag-qa-system 的 Schema 模式
"""

from pydantic import BaseModel, Field


# ===== 请求模型 =====

class OptimizeRequest(BaseModel):
    """优化请求"""
    jd_text: str = Field(..., min_length=10, max_length=10000, description="职位描述文本")


class JDParseRequest(BaseModel):
    """JD 解析请求"""
    jd_text: str = Field(..., min_length=10, max_length=10000, description="职位描述文本")


class MatchRequest(BaseModel):
    """技能匹配请求"""
    jd_skills: list[dict] = Field(..., description="JD提取的技能列表")
    resume_sections: dict = Field(..., description="解析后的简历段落")


class SuggestRequest(BaseModel):
    """建议生成请求"""
    jd_summary: str = Field(..., description="JD摘要")
    resume_sections: dict = Field(..., description="解析后的简历段落")
    match_results: list[dict] = Field(..., description="匹配结果")


class WriteRequest(BaseModel):
    """简历重写请求"""
    jd_summary: str = Field(..., description="JD摘要")
    resume_sections: dict = Field(..., description="解析后的简历段落")
    match_results: list[dict] = Field(..., description="匹配结果")
    suggestions: list[dict] = Field(..., description="优化建议")


# ===== 响应模型 =====

class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str = "ok"
    version: str = "1.0.0"
    message: str = "AI Resume Optimizer API is running"


class SkillItem(BaseModel):
    """技能项"""
    name: str
    category: str  # hard / soft / domain / tool
    proficiency: str  # required / preferred / nice-to-have
    source: str = "jd"  # jd / resume


class MatchResultItem(BaseModel):
    """匹配结果项"""
    skill: str
    status: str  # match / partial_match / missing
    score: float
    detail: str


class SuggestionItem(BaseModel):
    """优化建议项"""
    section: str  # summary / experience / skills / education / projects
    severity: str  # critical / recommended / optional
    original: str
    suggestion: str
    reason: str


class OptimizeResponse(BaseModel):
    """优化响应"""
    session_id: str
    jd_skills: list[dict] = Field(default_factory=list)
    jd_summary: str = ""
    resume_sections: dict = Field(default_factory=dict)
    match_results: list[dict] = Field(default_factory=list)
    match_summary: str = ""
    suggestions: list[dict] = Field(default_factory=list)
    optimized_resume_md: str = ""
    steps_completed: list[str] = Field(default_factory=list)


class SSEEvent(BaseModel):
    """SSE 事件"""
    type: str  # step_complete / token / done / error
    step: int = 0
    node: str = ""
    data: dict = Field(default_factory=dict)
    message: str = ""
