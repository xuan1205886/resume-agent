"""
Pytest 全局配置 — 共享 fixtures 和 Mock 工具
"""
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# 确保项目根目录在 sys.path 中
sys.path.insert(0, str(Path(__file__).parent.parent))

from langchain_core.messages import AIMessage


def make_mock_llm_response(response_data: dict | str) -> MagicMock:
    """创建一个模拟的 LLM 实例，invoke() 返回指定的响应

    Args:
        response_data: 如果是 dict，自动转为 JSON 字符串；如果是 str，直接返回

    Returns:
        MagicMock LLM 实例
    """
    if isinstance(response_data, dict):
        content = json.dumps(response_data, ensure_ascii=False)
    else:
        content = response_data

    mock_llm = MagicMock()
    mock_llm.invoke.return_value = AIMessage(content=content)
    return mock_llm


@pytest.fixture
def mock_jd_response():
    """模拟 JD 解析的 LLM 返回"""
    return {
        "position": "Python后端开发工程师",
        "company": "某科技公司",
        "summary": "负责后端系统开发与维护",
        "responsibilities": ["设计API接口", "优化数据库查询"],
        "skills": [
            {"name": "Python", "category": "hard", "proficiency": "required", "description": "精通Python编程"},
            {"name": "FastAPI", "category": "hard", "proficiency": "required", "description": "熟悉FastAPI框架"},
            {"name": "Docker", "category": "tool", "proficiency": "preferred", "description": "容器化部署"},
            {"name": "沟通能力", "category": "soft", "proficiency": "required", "description": "团队协作"},
        ],
        "education": "本科及以上",
        "experience_years": "3年以上",
        "other_requirements": ["有开源项目经验优先"],
    }


@pytest.fixture
def mock_resume_response():
    """模拟简历解析的 LLM 返回"""
    return {
        "contact": {
            "name": "张三",
            "email": "zhangsan@example.com",
            "phone": "13800138000",
            "location": "北京",
            "github": "github.com/zhangsan",
            "linkedin": "",
        },
        "summary": "Python后端开发工程师，3年经验",
        "skills": ["Python", "FastAPI", "Docker", "PostgreSQL", "Redis"],
        "experience": [
            {
                "company": "某互联网公司",
                "title": "后端开发工程师",
                "duration": "2022.01 - 至今",
                "bullets": [
                    "设计并实现RAG知识库问答系统，日均处理1000+次查询",
                    "使用FastAPI构建REST API服务，支持SSE流式输出",
                ],
            }
        ],
        "education": [
            {"school": "某大学", "degree": "本科", "major": "计算机科学", "duration": "2018-2022"},
        ],
        "projects": [
            {"name": "RAG问答系统", "tech_stack": "Python, LangChain, ChromaDB", "bullets": ["搭建Chroma向量数据库"]},
        ],
    }


@pytest.fixture
def mock_match_response():
    """模拟技能匹配的 LLM 返回"""
    return {
        "match_results": [
            {"skill": "Python", "status": "match", "score": 0.95, "detail": "简历中明确展示Python经验"},
            {"skill": "FastAPI", "status": "match", "score": 0.90, "detail": "有FastAPI项目经验"},
            {"skill": "Docker", "status": "partial_match", "score": 0.60, "detail": "有提及但不够深入"},
            {"skill": "Kubernetes", "status": "missing", "score": 0.0, "detail": "简历中未体现"},
        ],
        "match_summary": "候选人Python技能匹配度很高，但缺少Kubernetes经验",
        "overall_score": 0.65,
    }


@pytest.fixture
def mock_suggestion_response():
    """模拟优化建议的 LLM 返回"""
    return {
        "suggestions": [
            {
                "section": "experience",
                "severity": "critical",
                "original": "开发了RAG问答系统",
                "suggestion": "主导设计并实现基于LangChain的RAG知识库问答系统，优化检索流程，将查询准确率提升30%，日均处理1000+用户查询",
                "reason": "需要量化成果并使用动作动词开头",
            },
            {
                "section": "skills",
                "severity": "recommended",
                "original": "",
                "suggestion": "在技能部分增加Kubernetes和CI/CD相关技能描述",
                "reason": "JD要求有容器化部署经验",
            },
        ],
        "overall_advice": "重点优化工作经历的量化描述，补全缺失技能的展示",
    }
