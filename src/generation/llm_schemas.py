"""
LLM 输出 Pydantic Schema — 结构化校验所有 LLM 返回结果
防止 LLM 返回格式错误、类型错误、范围异常的数据
"""

from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


# ===== JD 解析 =====


class JDSkillItem(BaseModel):
    """JD 技能项"""
    name: str = ""
    category: str = Field(default="hard", description="hard/soft/tool/domain")
    proficiency: str = Field(default="required", description="required/preferred/nice-to-have")
    description: str = ""


class JDParseResult(BaseModel):
    """JD 解析结果"""
    position: str = ""
    company: str = ""
    summary: str = ""
    responsibilities: List[str] = Field(default_factory=list)
    skills: List[JDSkillItem] = Field(default_factory=list)
    education: str = ""
    experience_years: str = ""
    other_requirements: List[str] = Field(default_factory=list)

    @field_validator("skills", mode="before")
    @classmethod
    def filter_invalid_skills(cls, v: list) -> list:
        """过滤掉名称为空的技能项"""
        if not isinstance(v, list):
            return []
        return [s for s in v if isinstance(s, dict) and s.get("name", "").strip()]


# ===== 简历解析 =====


class ContactInfo(BaseModel):
    """联系方式"""
    name: str = ""
    email: str = ""
    phone: str = ""
    location: str = ""
    github: str = ""
    linkedin: str = ""


class ExperienceEntry(BaseModel):
    """工作经历"""
    company: str = ""
    title: str = ""
    duration: str = ""
    bullets: List[str] = Field(default_factory=list)


class EducationEntry(BaseModel):
    """教育经历"""
    school: str = ""
    degree: str = ""
    major: str = ""
    duration: str = ""


class ProjectEntry(BaseModel):
    """项目经历"""
    name: str = ""
    tech_stack: str = ""
    bullets: List[str] = Field(default_factory=list)


class ResumeParseResult(BaseModel):
    """简历解析结果"""
    contact: ContactInfo = Field(default_factory=ContactInfo)
    summary: str = ""
    skills: List[str] = Field(default_factory=list)
    experience: List[ExperienceEntry] = Field(default_factory=list)
    education: List[EducationEntry] = Field(default_factory=list)
    projects: List[ProjectEntry] = Field(default_factory=list)


# ===== 技能匹配 =====


class MatchResultItem(BaseModel):
    """技能匹配项"""
    skill: str = ""
    status: str = Field(default="missing", description="match/partial_match/missing/mismatch")
    score: float = Field(default=0.0)
    detail: str = ""

    @field_validator("score", mode="before")
    @classmethod
    def clamp_score(cls, v: float) -> float:
        """确保分数在 0-1 之间（before 模式：先钳制再通过 Field 校验）"""
        return max(0.0, min(1.0, float(v)))

    @field_validator("status", mode="before")
    @classmethod
    def validate_status(cls, v: str) -> str:
        """校验状态值"""
        valid = {"match", "partial_match", "missing", "mismatch"}
        if v not in valid:
            return "missing"
        return v


class MatchAnalysisResult(BaseModel):
    """技能匹配分析结果"""
    match_results: List[MatchResultItem] = Field(default_factory=list)
    match_summary: str = ""
    overall_score: float = Field(default=0.0)

    @field_validator("overall_score", mode="before")
    @classmethod
    def clamp_overall_score(cls, v: float) -> float:
        """规范化分数：如果 LLM 返回了百分制（>1.0），转为小数"""
        v = float(v)
        if v > 1.0:
            return v / 100.0
        return max(0.0, min(1.0, v))


# ===== 优化建议 =====


class SuggestionItem(BaseModel):
    """优化建议"""
    section: str = Field(default="", description="summary/experience/skills/education/projects/format")
    severity: str = Field(default="recommended", description="critical/recommended/optional")
    original: str = ""
    suggestion: str = ""
    reason: str = ""

    @field_validator("severity", mode="before")
    @classmethod
    def validate_severity(cls, v: str) -> str:
        """校验严重程度"""
        valid = {"critical", "recommended", "optional"}
        if v not in valid:
            return "recommended"
        return v


class SuggestionResult(BaseModel):
    """优化建议结果"""
    suggestions: List[SuggestionItem] = Field(default_factory=list)
    overall_advice: str = ""

    @field_validator("suggestions", mode="before")
    @classmethod
    def filter_empty_suggestions(cls, v: list) -> list:
        """过滤掉建议文本为空的条目"""
        if not isinstance(v, list):
            return []
        return [
            s for s in v
            if isinstance(s, dict) and (s.get("suggestion", "").strip() or s.get("reason", "").strip())
        ]


# ===== 块级组装 — Bullet 提取 & 评分 =====


class BulletItem(BaseModel):
    """单条简历 bullet（来自 experience 或 project）"""
    id: str = ""                              # 唯一标识
    text: str = ""                            # 原始 bullet 文本
    source_type: str = "experience"           # experience / project
    company: str = ""                         # 所属公司（experience）
    title: str = ""                           # 职位（experience）
    duration: str = ""                        # 时间段
    project_name: str = ""                    # 项目名（project）
    tech_stack: str = ""                      # 技术栈（project）
    is_recent: bool = False                   # 是否最近经历


class BulletScore(BaseModel):
    """一条带评分的 bullet"""
    bullet: BulletItem
    jd_skill_score: float = 0.0               # 匹配 JD 技能的得分
    quantified_score: float = 0.0             # 量化数字得分
    action_verb_score: float = 0.0            # 动作动词得分
    recency_score: float = 0.0               # 时效性得分
    total_score: float = 0.0                  # 总分
    matched_skills: List[str] = Field(default_factory=list)  # 匹配到的 JD 技能名


class ScoredBulletList(BaseModel):
    """评分后的 bullet 列表"""
    bullets: List[BulletScore] = Field(default_factory=list)
    total_bullets_in_pool: int = 0


# ===== Fact-Drift 检查 =====


class FactCheckVerdict(BaseModel):
    """单条 bullet 的事实核查结论"""
    bullet_id: str = ""                       # 对应 scored_bullet 的 ID
    generated_text: str = ""                  # 生成的 bullet 文本
    original_text: str = ""                   # 最接近的原始 bullet 文本
    drift_level: str = "none"                 # none / minor / major / fabricated
    explanation: str = ""                     # 判断理由
    added_facts: List[str] = Field(default_factory=list)    # 新增的事实
    missing_facts: List[str] = Field(default_factory=list)  # 丢失的事实


class FactCheckReport(BaseModel):
    """完整的事实核查报告"""
    verdicts: List[FactCheckVerdict] = Field(default_factory=list)
    overall_trust_score: float = 1.0          # 整体可信度 (0-1)
    summary: str = ""                         # 核查摘要
    none_count: int = 0
    minor_count: int = 0
    major_count: int = 0
    fabricated_count: int = 0

    @field_validator("overall_trust_score", mode="before")
    @classmethod
    def clamp_trust_score(cls, v: float) -> float:
        return max(0.0, min(1.0, float(v)))


# ===== Bullet 重排序（LLM 辅助） =====


class BulletReorderResult(BaseModel):
    """LLM 对 bullet 排序的调整建议"""
    bullet_ids_ordered: List[str] = Field(default_factory=list)  # 建议的 ID 顺序
    reasoning: str = ""                                           # 排序理由
