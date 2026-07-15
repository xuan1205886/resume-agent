"""
LLM Schema 校验单元测试 — 验证 Pydantic 模型对异常数据的处理
"""

import pytest
from pydantic import ValidationError

from src.generation.llm_schemas import (
    JDSkillItem,
    JDParseResult,
    MatchResultItem,
    MatchAnalysisResult,
    SuggestionItem,
    SuggestionResult,
    ResumeParseResult,
    ContactInfo,
    ExperienceEntry,
)


class TestJDSchemas:
    """JD 解析 Schema 测试"""

    def test_valid_skill_item(self):
        skill = JDSkillItem(name="Python", category="hard", proficiency="required")
        assert skill.name == "Python"

    def test_skill_item_defaults(self):
        skill = JDSkillItem()
        assert skill.name == ""
        assert skill.category == "hard"

    def test_empty_skills_filtered(self):
        result = JDParseResult(
            position="工程师",
            skills=[
                {"name": "Python", "category": "hard"},
                {"name": "", "category": "soft"},  # 空名称应被过滤
                {"name": "Docker", "category": "tool"},
            ],
        )
        assert len(result.skills) == 2
        assert result.skills[0].name == "Python"


class TestMatchSchemas:
    """匹配 Schema 测试"""

    def test_score_clamped_to_range(self):
        item = MatchResultItem(skill="Python", status="match", score=95.0)
        assert item.score == 1.0  # 钳制到最大值

        item2 = MatchResultItem(skill="Java", status="missing", score=-5.0)
        assert item2.score == 0.0  # 钳制到最小值

    def test_overall_score_percentage_conversion(self):
        """测试百分制分数自动转换为小数"""
        result = MatchAnalysisResult(
            overall_score=85.0,  # 百分制
            match_results=[],
            match_summary="",
        )
        assert result.overall_score == 0.85

    def test_status_validation(self):
        item = MatchResultItem(skill="Python", status="invalid", score=0.5)
        assert item.status == "missing"  # 回退到默认


class TestSuggestionSchemas:
    """建议 Schema 测试"""

    def test_severity_validation(self):
        item = SuggestionItem(
            section="skills",
            severity="invalid",
            suggestion="建议内容",
            reason="原因",
        )
        assert item.severity == "recommended"  # 回退

    def test_empty_suggestions_filtered(self):
        result = SuggestionResult(
            suggestions=[
                {"section": "", "severity": "optional", "suggestion": "", "reason": ""},
            ],
            overall_advice="",
        )
        assert len(result.suggestions) == 0


class TestResumeSchemas:
    """简历 Schema 测试"""

    def test_contact_defaults(self):
        contact = ContactInfo()
        assert contact.name == ""
        assert contact.email == ""

    def test_experience_entry(self):
        exp = ExperienceEntry(
            company="某公司",
            title="开发工程师",
            bullets=["完成任务A", "优化系统B"],
        )
        assert len(exp.bullets) == 2

    def test_full_resume_parse(self):
        result = ResumeParseResult(
            contact={"name": "张三", "email": "test@test.com"},
            skills=["Python", "SQL"],
            experience=[{"company": "某公司", "title": "开发", "bullets": ["任务"]}],
        )
        assert result.contact.name == "张三"
        assert len(result.skills) == 2
