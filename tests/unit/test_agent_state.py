"""
Agent State 单元测试 — 纯数据状态测试，无需 Mock
"""

from src.agent.state import create_initial_state, AgentState


def test_create_initial_state():
    """测试创建初始状态"""
    state = create_initial_state("JD文本", "简历文本")
    assert state["jd_text"] == "JD文本"
    assert state["resume_text"] == "简历文本"
    assert state["jd_skills"] == []
    assert state["match_results"] == []
    assert state["optimized_resume_md"] == ""


def test_initial_state_has_all_fields():
    """测试初始状态包含所有必需字段"""
    state = create_initial_state("", "")
    required_keys = [
        "jd_text", "resume_text", "jd_skills", "jd_summary",
        "resume_sections", "match_results", "suggestions",
        "optimized_resume_md", "error",
    ]
    for key in required_keys:
        assert key in state, f"缺少字段: {key}"


def test_initial_state_empty_strings():
    """测试空字符串输入"""
    state = create_initial_state("", "")
    assert state["jd_text"] == ""
    assert state["resume_text"] == ""
    assert state["overall_score"] == 0.0
    assert state["messages"] == []


def test_initial_state_default_values():
    """测试默认值类型正确"""
    state = create_initial_state("JD", "简历")
    assert isinstance(state["jd_skills"], list)
    assert isinstance(state["match_results"], list)
    assert isinstance(state["suggestions"], list)
    assert isinstance(state["overall_score"], float)
    assert isinstance(state["error"], str)


def test_initial_state_is_typeddict():
    """测试状态是 TypedDict 兼容的"""
    state = create_initial_state("JD", "简历")
    # AgentState 是 TypedDict，应能像字典一样使用
    keys = list(state.keys())
    assert "jd_text" in keys
    assert "resume_text" in keys
