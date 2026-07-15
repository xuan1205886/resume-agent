"""
Bullet 提取器单元测试 — 纯代码测试
"""

from src.optimization.bullet_extractor import extract_bullet_pool, get_bullet_context
from src.generation.llm_schemas import BulletItem


def test_extract_empty_resume():
    """空简历返回空列表"""
    result = extract_bullet_pool({})
    assert result == []


def test_extract_experience_bullets():
    """提取工作经历 bullets"""
    parsed = {
        "experience": [
            {
                "company": "某公司",
                "title": "后端开发",
                "duration": "2022-2024",
                "bullets": ["开发RAG系统", "优化API性能"],
            }
        ],
        "projects": [],
    }
    result = extract_bullet_pool(parsed)
    assert len(result) == 2
    assert result[0].text == "开发RAG系统"
    assert result[0].source_type == "experience"
    assert result[0].company == "某公司"
    assert result[0].title == "后端开发"
    assert result[0].is_recent is True  # 第一条经历


def test_extract_project_bullets():
    """提取项目 bullets"""
    parsed = {
        "experience": [],
        "projects": [
            {
                "name": "RAG问答系统",
                "tech_stack": "Python, LangChain",
                "bullets": ["搭建Chroma向量库", "实现流式输出"],
            }
        ],
    }
    result = extract_bullet_pool(parsed)
    assert len(result) == 2
    assert result[0].text == "搭建Chroma向量库"
    assert result[0].source_type == "project"
    assert result[0].project_name == "RAG问答系统"


def test_extract_skips_empty_bullets():
    """跳过空文本 bullet"""
    parsed = {
        "experience": [
            {"company": "某公司", "bullets": ["有效bullet", "", "  ", None]},
        ],
        "projects": [],
    }
    result = extract_bullet_pool(parsed)
    assert len(result) == 1
    assert result[0].text == "有效bullet"


def test_get_bullet_context_experience():
    """获取经历 bullet 上下文"""
    bullet = BulletItem(
        id="test_1",
        text="开发系统",
        source_type="experience",
        company="某科技公司",
        title="Python开发",
        duration="2022-2024",
    )
    ctx = get_bullet_context(bullet)
    assert "某科技公司" in ctx
    assert "Python开发" in ctx


def test_get_bullet_context_project():
    """获取项目 bullet 上下文"""
    bullet = BulletItem(
        id="test_2",
        text="实现功能",
        source_type="project",
        project_name="RAG系统",
        tech_stack="Python, FastAPI",
    )
    ctx = get_bullet_context(bullet)
    assert "RAG系统" in ctx
    assert "Python" in ctx
