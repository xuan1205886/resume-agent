"""
简历解析器单元测试 — 使用 Mock 替代真实 API 调用
"""

from unittest.mock import patch

from src.parsing.resume_parser import structure_resume, build_resume_sections
from src.generation.output_validator import LLMOutputError


def test_structure_resume_returns_expected_fields(mock_resume_response):
    """测试结构化解析返回所有字段"""
    resume = "张三\nPython开发工程师\n技能：Python, FastAPI, Docker"

    with patch("src.parsing.resume_parser.get_llm") as mock_get_llm:
        from tests.conftest import make_mock_llm_response
        mock_get_llm.return_value = make_mock_llm_response(mock_resume_response)

        result = structure_resume(resume)

    assert "contact" in result
    assert "skills" in result
    assert "experience" in result
    assert "education" in result
    assert "projects" in result
    assert result["contact"]["name"] == "张三"
    assert "Python" in result["skills"]


def test_structure_resume_raises_on_empty():
    """测试空文本输入应抛出异常"""
    try:
        structure_resume("")
        assert False, "应该抛出 ValueError"
    except ValueError:
        pass


def test_structure_resume_raises_on_whitespace():
    """测试纯空白文本应抛出异常"""
    try:
        structure_resume("   \n  ")
        assert False, "应该抛出 ValueError"
    except ValueError:
        pass


def test_build_resume_sections():
    """测试构建简历段落"""
    parsed = {
        "contact": {"name": "张三"},
        "summary": "后端开发工程师",
        "skills": ["Python", "SQL"],
        "experience": [
            {"company": "某公司", "title": "开发", "duration": "2022-2024", "bullets": ["开发系统"]}
        ],
        "education": [],
        "projects": [],
    }
    sections = build_resume_sections(parsed)
    assert "summary" in sections
    assert "skills" in sections
    assert "experience" in sections
    assert "Python" in sections["skills"]
    assert sections["summary"] == "后端开发工程师"


def test_build_resume_sections_with_multiple_experiences():
    """测试多条工作经历的段落构建"""
    parsed = {
        "contact": {},
        "summary": "",
        "skills": [],
        "experience": [
            {"company": "公司A", "title": "开发", "duration": "2022-2024", "bullets": ["任务1"]},
            {"company": "公司B", "title": "实习", "duration": "2021-2022", "bullets": ["任务2"]},
        ],
        "education": [
            {"school": "大学", "degree": "本科", "major": "CS", "duration": "2018-2022"},
        ],
        "projects": [],
    }
    sections = build_resume_sections(parsed)
    assert "公司A" in sections["experience"]
    assert "公司B" in sections["experience"]
    assert "大学" in sections["education"]


def test_structure_resume_handles_llm_output_error(mock_resume_response):
    """测试 LLM 返回无效 JSON 时抛出异常"""
    resume = "测试简历文本"

    with patch("src.parsing.resume_parser.get_llm") as mock_get_llm:
        from tests.conftest import make_mock_llm_response
        mock_get_llm.return_value = make_mock_llm_response("无效JSON")

        try:
            structure_resume(resume)
            assert False, "应该抛出 LLMOutputError"
        except LLMOutputError:
            pass
