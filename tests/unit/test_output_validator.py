"""
输出校验器单元测试
"""

import json
import pytest

from src.generation.output_validator import (
    extract_json_from_text,
    parse_and_validate,
    LLMOutputError,
)
from src.generation.llm_schemas import (
    JDParseResult,
    MatchAnalysisResult,
    SuggestionResult,
    MatchResultItem,
)


class TestExtractJsonFromText:
    """JSON 提取测试"""

    def test_pure_json(self):
        content = '{"key": "value"}'
        result = extract_json_from_text(content)
        assert result == '{"key": "value"}'

    def test_markdown_code_block(self):
        content = '```json\n{"key": "value"}\n```'
        result = extract_json_from_text(content)
        assert "key" in result
        assert "value" in result

    def test_markdown_code_block_no_lang(self):
        content = '```\n{"key": "value"}\n```'
        result = extract_json_from_text(content)
        assert "key" in result

    def test_json_with_prefix_text(self):
        content = '这是一些说明文字\n{"key": "value"}'
        result = extract_json_from_text(content)
        assert result == '{"key": "value"}'

    def test_json_with_suffix_text(self):
        content = '{"key": "value"}\n这是额外的文字'
        result = extract_json_from_text(content)
        assert result == '{"key": "value"}'


class TestParseAndValidate:
    """解析校验测试"""

    def test_valid_jd_result(self, mock_jd_response):
        content = json.dumps(mock_jd_response, ensure_ascii=False)
        result = parse_and_validate(content, JDParseResult, context="测试")
        assert result.position == "Python后端开发工程师"
        assert len(result.skills) == 4

    def test_score_clamping(self):
        """测试分数钳制到 0-1"""
        content = json.dumps({
            "match_results": [
                {"skill": "Python", "status": "match", "score": 95.0, "detail": ""}
            ],
            "match_summary": "",
            "overall_score": 95.0,  # 百分制 → 应为 0.95
        })
        result = parse_and_validate(content, MatchAnalysisResult, context="测试")
        assert result.overall_score <= 1.0
        assert result.match_results[0].score <= 1.0

    def test_invalid_json_raises(self):
        content = "这不是JSON"
        with pytest.raises(LLMOutputError):
            parse_and_validate(content, JDParseResult, context="测试")

    def test_invalid_status_defaults(self):
        """测试无效 status 值回退为默认"""
        content = json.dumps({
            "match_results": [
                {"skill": "Python", "status": "invalid_status", "score": 0.8, "detail": ""}
            ],
            "match_summary": "",
            "overall_score": 0.5,
        })
        result = parse_and_validate(content, MatchAnalysisResult, context="测试")
        assert result.match_results[0].status == "missing"  # 回退到默认

    def test_empty_suggestions_filtered(self):
        """测试空建议被过滤"""
        content = json.dumps({
            "suggestions": [
                {"section": "skills", "severity": "recommended", "original": "", "suggestion": "", "reason": ""},
                {"section": "experience", "severity": "critical", "original": "原文", "suggestion": "修改建议", "reason": "原因"},
            ],
            "overall_advice": "整体建议",
        })
        result = parse_and_validate(content, SuggestionResult, context="测试")
        # 空建议应被过滤
        assert len(result.suggestions) == 1

    def test_severity_validation(self):
        """测试严重程度校验"""
        content = json.dumps({
            "suggestions": [
                {"section": "skills", "severity": "invalid_severity", "suggestion": "建议", "reason": "原因"},
            ],
            "overall_advice": "",
        })
        result = parse_and_validate(content, SuggestionResult, context="测试")
        assert result.suggestions[0].severity == "recommended"  # 回退到默认
