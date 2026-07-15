"""
Bullet 评分器单元测试 — 纯规则打分（不调 LLM）
"""

from src.optimization.bullet_scorer import score_bullets
from src.optimization.bullet_extractor import extract_bullet_pool


def make_parsed_resume(bullets: list[str]) -> dict:
    """快速创建包含 bullets 的解析简历"""
    return {
        "experience": [
            {
                "company": "某科技公司",
                "title": "后端开发工程师",
                "duration": "2022.01 - 至今",
                "bullets": bullets,
            }
        ],
        "projects": [],
    }


def test_score_empty_bullets():
    """空 bullet 列表不报错"""
    result = score_bullets([], [], [])
    assert result.total_bullets_in_pool == 0
    assert result.bullets == []


def test_score_quantified_bullet():
    """含量化数字的 bullet 得分更高"""
    parsed = make_parsed_resume(["设计并实现RAG系统，日均处理1000+次查询，准确率提升30%"])
    bullets = extract_bullet_pool(parsed)

    result = score_bullets(bullets, [], [])
    assert len(result.bullets) == 1
    # 有量化数字 + 有动作动词 + 是最近经历
    assert result.bullets[0].quantified_score > 0
    assert result.bullets[0].action_verb_score > 0
    assert result.bullets[0].total_score > 0


def test_score_jd_skill_match():
    """包含 JD 技能的 bullet 得分更高"""
    parsed = make_parsed_resume(["使用Python和FastAPI构建REST API服务"])
    bullets = extract_bullet_pool(parsed)

    jd_skills = [
        {"name": "Python", "category": "hard"},
        {"name": "FastAPI", "category": "hard"},
    ]
    match_results = [
        {"skill": "Python", "status": "match"},
        {"skill": "FastAPI", "status": "match"},
    ]

    result = score_bullets(bullets, jd_skills, match_results)
    assert len(result.bullets) == 1
    assert result.bullets[0].jd_skill_score > 0
    assert "python" in result.bullets[0].matched_skills
    assert "fastapi" in result.bullets[0].matched_skills


def test_score_multiple_bullets_sorted():
    """多条 bullets 按总分降序排列"""
    parsed = make_parsed_resume([
        "主导设计并实现RAG系统，日均处理1000+查询，使用Python和FastAPI技术栈",
        "负责日常维护",
        "编写技术文档",
    ])
    bullets = extract_bullet_pool(parsed)

    jd_skills = [
        {"name": "Python", "category": "hard"},
        {"name": "FastAPI", "category": "hard"},
    ]
    match_results = [
        {"skill": "Python", "status": "match"},
        {"skill": "FastAPI", "status": "match"},
    ]

    result = score_bullets(bullets, jd_skills, match_results)
    assert len(result.bullets) == 3
    # 第1条（含量化+动作动词+技能匹配）应排第一，分数最高
    assert result.bullets[0].total_score > result.bullets[1].total_score
    # 第3条"编写技术文档"应排最后（无技能匹配、无量化、无动作动词）
    assert "编写" in result.bullets[2].bullet.text


def test_score_first_experience_is_recent():
    """第一条经历标记为最近"""
    parsed = {
        "experience": [
            {"company": "公司A", "title": "开发", "duration": "2024-至今", "bullets": ["开发A"]},
            {"company": "公司B", "title": "实习", "duration": "2022-2024", "bullets": ["实习B"]},
        ],
        "projects": [],
    }
    bullets = extract_bullet_pool(parsed)
    result = score_bullets(bullets, [], [])
    assert result.bullets[0].recency_score > 0  # 最近经历
    # 第二条 bullet 应该没有时效分（非第一条经历）
    non_recent = [b for b in result.bullets if not b.bullet.is_recent]
    if non_recent:
        assert non_recent[0].recency_score == 0.0
