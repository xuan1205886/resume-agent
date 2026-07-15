"""
Bullet 提取器 — 从结构化简历数据中提取所有 bullet points
纯 Python 实现，不调用 LLM
"""

import hashlib
from typing import List

from src.generation.llm_schemas import BulletItem


def extract_bullet_pool(parsed_resume: dict) -> List[BulletItem]:
    """从 parsed_resume 中提取所有 work experience 和 project bullets

    每个 bullet 被打上来源标记（公司、职位、时间段等），
    用于后续 JD 匹配打分和组装时的溯源。

    Args:
        parsed_resume: structure_resume() 返回的结构化简历数据

    Returns:
        BulletItem 列表，按 experience → projects 顺序排列
    """
    bullets: List[BulletItem] = []

    # 1. 提取工作经历 bullets
    experience_list = parsed_resume.get("experience", [])
    if isinstance(experience_list, dict):
        experience_list = [experience_list]

    for i, exp in enumerate(experience_list):
        if not isinstance(exp, dict):
            continue
        exp_bullets = exp.get("bullets", [])
        if isinstance(exp_bullets, str):
            exp_bullets = [exp_bullets]

        company = exp.get("company", "")
        title = exp.get("title", "")
        duration = exp.get("duration", "")

        for j, bullet_text in enumerate(exp_bullets):
            if not bullet_text or not bullet_text.strip():
                continue
            bullet_id = _make_bullet_id("exp", i, j, bullet_text)
            bullets.append(BulletItem(
                id=bullet_id,
                text=bullet_text.strip(),
                source_type="experience",
                company=company,
                title=title,
                duration=duration,
                is_recent=(i == 0),  # 第一条经历视为最近
            ))

    # 2. 提取项目经历 bullets
    projects_list = parsed_resume.get("projects", [])
    if isinstance(projects_list, dict):
        projects_list = [projects_list]

    for i, proj in enumerate(projects_list):
        if not isinstance(proj, dict):
            continue
        proj_bullets = proj.get("bullets", [])
        if isinstance(proj_bullets, str):
            proj_bullets = [proj_bullets]

        proj_name = proj.get("name", "")
        tech_stack = proj.get("tech_stack", "")

        for j, bullet_text in enumerate(proj_bullets):
            if not bullet_text or not bullet_text.strip():
                continue
            bullet_id = _make_bullet_id("proj", i, j, bullet_text)
            bullets.append(BulletItem(
                id=bullet_id,
                text=bullet_text.strip(),
                source_type="project",
                project_name=proj_name,
                tech_stack=tech_stack,
            ))

    return bullets


def get_bullet_context(bullet: BulletItem) -> str:
    """获取 bullet 的上下文描述（用于 LLM prompt）

    Returns:
        格式: "[公司] 职位 | 时间段" 或 "[项目] 项目名 | 技术栈"
    """
    if bullet.source_type == "experience":
        parts = []
        if bullet.company:
            parts.append(bullet.company)
        if bullet.title:
            parts.append(bullet.title)
        if bullet.duration:
            parts.append(bullet.duration)
        return " | ".join(parts) if parts else ""
    else:
        parts = []
        if bullet.project_name:
            parts.append(f"项目: {bullet.project_name}")
        if bullet.tech_stack:
            parts.append(f"技术栈: {bullet.tech_stack}")
        return " | ".join(parts) if parts else ""


def _make_bullet_id(source_type: str, entry_index: int, bullet_index: int, text: str) -> str:
    """生成稳定的 bullet ID"""
    short_hash = hashlib.md5(text[:100].encode()).hexdigest()[:8]
    return f"{source_type}_{entry_index}_{bullet_index}_{short_hash}"
