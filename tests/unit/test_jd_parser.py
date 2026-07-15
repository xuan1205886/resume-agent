"""
JD 解析器单元测试 — 使用 Mock 替代真实 API 调用
"""

from unittest.mock import patch

from src.parsing.jd_parser import parse_jd, extract_jd_skills_only
from src.generation.output_validator import LLMOutputError


def test_parse_jd_extracts_skills(mock_jd_response):
    """测试 JD 解析能提取技能"""
    jd = "岗位要求：精通Python编程"

    with patch("src.parsing.jd_parser.get_llm") as mock_get_llm:
        from tests.conftest import make_mock_llm_response
        mock_get_llm.return_value = make_mock_llm_response(mock_jd_response)

        result = parse_jd(jd)

    assert "skills" in result
    assert isinstance(result["skills"], list)
    assert len(result["skills"]) == 4
    assert result["skills"][0]["name"] == "Python"
    assert result["position"] == "Python后端开发工程师"


def test_parse_jd_raises_on_empty():
    """测试空 JD 输入应抛出异常"""
    with patch("src.parsing.jd_parser.get_llm") as mock_get_llm:
        from tests.conftest import make_mock_llm_response
        mock_get_llm.return_value = make_mock_llm_response({})

        try:
            parse_jd("")
            assert False, "应该抛出 ValueError"
        except ValueError:
            pass  # 预期行为


def test_parse_jd_raises_on_whitespace_only():
    """测试纯空白 JD 输入应抛出异常"""
    try:
        parse_jd("   ")
        assert False, "应该抛出 ValueError"
    except ValueError:
        pass


def test_extract_jd_skills_only(mock_jd_response):
    """测试仅提取技能"""
    jd = "要求：精通Python和SQL"

    with patch("src.parsing.jd_parser.get_llm") as mock_get_llm:
        from tests.conftest import make_mock_llm_response
        mock_get_llm.return_value = make_mock_llm_response(mock_jd_response)

        skills = extract_jd_skills_only(jd)

    assert isinstance(skills, list)
    assert len(skills) > 0
    assert any(s["name"] == "Python" for s in skills)


def test_parse_jd_returns_fields(mock_jd_response):
    """测试返回所有必需字段"""
    jd = "测试JD"

    with patch("src.parsing.jd_parser.get_llm") as mock_get_llm:
        from tests.conftest import make_mock_llm_response
        mock_get_llm.return_value = make_mock_llm_response(mock_jd_response)

        result = parse_jd(jd)

    required_fields = ["position", "company", "summary", "responsibilities", "skills", "education"]
    for field in required_fields:
        assert field in result, f"缺少字段: {field}"


def test_parse_jd_handles_llm_output_error(mock_jd_response):
    """测试 LLM 返回无效 JSON 时抛出异常（不再静默吞掉）"""
    jd = "测试JD"

    with patch("src.parsing.jd_parser.get_llm") as mock_get_llm:
        from tests.conftest import make_mock_llm_response
        # 返回无效 JSON
        mock_llm = make_mock_llm_response("这不是合法的JSON输出")
        mock_get_llm.return_value = mock_llm

        try:
            parse_jd(jd)
            assert False, "应该抛出 LLMOutputError"
        except LLMOutputError:
            pass  # 预期行为


def test_parse_jd_handles_skill_validation(mock_jd_response):
    """测试技能项校验：空名称技能应被过滤"""
    jd = "测试JD"
    response = dict(mock_jd_response)
    response["skills"].append({"name": "", "category": "hard", "proficiency": "required"})

    with patch("src.parsing.jd_parser.get_llm") as mock_get_llm:
        from tests.conftest import make_mock_llm_response
        mock_get_llm.return_value = make_mock_llm_response(response)

        result = parse_jd(jd)

    # 空名称技能应被过滤
    skill_names = [s["name"] for s in result["skills"]]
    assert "" not in skill_names
