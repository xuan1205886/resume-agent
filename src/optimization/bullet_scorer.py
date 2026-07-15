"""
Bullet 评分器 — 规则打分 + LLM 辅助排序
纯 Python 打分优先，LLM 只做排序验证
"""

import json
import logging
import re
from typing import List

from langchain_core.messages import HumanMessage, SystemMessage

from src.generation.llm import get_llm
from src.generation.llm_schemas import BulletItem, BulletScore, ScoredBulletList, BulletReorderResult
from src.generation.output_validator import LLMOutputError, parse_and_validate
from src.optimization.bullet_extractor import get_bullet_context

logger = logging.getLogger("bullet_scorer")

# 动作动词列表（中文 + 英文）
ACTION_VERBS = {
    # 中文
    "设计", "实现", "主导", "优化", "构建", "开发", "搭建", "重构",
    "提升", "降低", "减少", "缩短", "增加", "扩大", "改进", "完善",
    "制定", "推动", "负责", "管理", "协调", "带领", "指导", "培训",
    "分析", "调研", "评估", "监控", "维护", "部署", "迁移", "集成",
    # 英文
    "designed", "implemented", "led", "optimized", "built", "developed",
    "architected", "improved", "reduced", "increased", "managed", "created",
    "deployed", "migrated", "integrated", "automated", "established",
    "launched", "scaled", "delivered",
}

# 量化数字正则
QUANTIFIED_PATTERNS = [
    re.compile(r'\d+\.?\d*\s*%'),          # 百分比: 30%, 12.5%
    re.compile(r'\d+\.?\d*\s*[倍xX]'),      # 倍数: 3倍, 2x
    re.compile(r'[日周月年]\s*均\s*\d+'),    # 日均: 日均1000
    re.compile(r'\d+\s*[万千百万亿]'),        # 数量: 10万, 1000万
    re.compile(r'\d+\s*[次条个人个]'),        # 计数: 100次, 50人
    re.compile(r'\d+\s*[元美元]'),           # 金额: 100万元
    re.compile(r'\b\d+[KkMm]\b'),           # 英文: 100K, 10M
    re.compile(r'\d+\s*[+＋]\s*'),          # 数字+加号
]

# 评分权重
WEIGHT_JD_SKILL = 3.0    # 匹配一个 JD 技能
WEIGHT_QUANTIFIED = 2.0  # 含量化数字
WEIGHT_ACTION_VERB = 1.0 # 含动作动词
WEIGHT_RECENCY = 1.0     # 最近经历

# 默认选取的 bullet 数量
DEFAULT_TOP_N = 10


def score_bullets(
    bullets: List[BulletItem],
    jd_skills: List[dict],
    match_results: List[dict],
    top_n: int = DEFAULT_TOP_N,
) -> ScoredBulletList:
    """对 bullet pool 进行规则打分并选出 top-N

    评分规则（纯代码）：
    1. JD 技能匹配分 — bullet 文本中包含已匹配的 JD 技能
    2. 量化数字分 — bullet 中包含具体的数字/指标
    3. 动作动词分 — bullet 以强有力的动作动词开头
    4. 时效性分 — 来自最近的经历

    Args:
        bullets: 从简历提取的所有 bullets
        jd_skills: JD 技能列表
        match_results: 技能匹配结果
        top_n: 选取前 N 条

    Returns:
        ScoredBulletList 包含排序后的评分结果
    """
    # 构建技能匹配词典：技能名 → 匹配状态
    matched_skill_names = set()
    for r in match_results:
        if r.get("status") in ("match", "partial_match"):
            matched_skill_names.add(r.get("skill", "").lower())

    # 收集所有 JD 技能名用于后续匹配
    all_jd_skill_names = set()
    for s in jd_skills:
        name = s.get("name", "").lower()
        if name:
            all_jd_skill_names.add(name)

    scored = []
    for bullet in bullets:
        text_lower = bullet.text.lower()

        # 1. JD 技能匹配分
        jd_score = 0.0
        matched = []
        for skill_name in all_jd_skill_names:
            # 支持中英文技能名匹配（子串匹配）
            if skill_name and (skill_name in text_lower or _partial_match(skill_name, text_lower)):
                jd_score += WEIGHT_JD_SKILL
                matched.append(skill_name)

        # 2. 量化数字分
        quantified_score = 0.0
        for pattern in QUANTIFIED_PATTERNS:
            if pattern.search(bullet.text):
                quantified_score = WEIGHT_QUANTIFIED
                break

        # 3. 动作动词分
        verb_score = 0.0
        for verb in ACTION_VERBS:
            if text_lower.startswith(verb.lower()):
                verb_score = WEIGHT_ACTION_VERB
                break
        if verb_score == 0.0:
            # 检查第二个字符起（中文可能带前缀如"负责设计..."）
            for verb in ACTION_VERBS:
                if verb.lower() in text_lower[:20]:
                    verb_score = WEIGHT_ACTION_VERB * 0.5
                    break

        # 4. 时效性分
        recency_score = WEIGHT_RECENCY if bullet.is_recent else 0.0

        total = jd_score + quantified_score + verb_score + recency_score
        scored.append(BulletScore(
            bullet=bullet,
            jd_skill_score=jd_score,
            quantified_score=quantified_score,
            action_verb_score=verb_score,
            recency_score=recency_score,
            total_score=total,
            matched_skills=matched,
        ))

    # 按总分降序排列
    scored.sort(key=lambda s: s.total_score, reverse=True)

    # 选出 top-N
    scored = scored[:top_n]

    return ScoredBulletList(
        bullets=scored,
        total_bullets_in_pool=len(bullets),
    )


def llm_reorder_bullets(
    scored_bullets: List[BulletScore],
    jd_summary: str,
    jd_position: str,
) -> List[BulletScore]:
    """使用 LLM 验证和微调 bullet 排序

    LLM 根据 JD 要求判断当前的规则排序是否合理，
    返回建议的 bullet ID 顺序。只做排序调整，不做内容改写。

    Args:
        scored_bullets: 规则打分后的 top bullets
        jd_summary: JD 摘要
        jd_position: 目标岗位

    Returns:
        重新排序后的 bullet 列表
    """
    if len(scored_bullets) <= 3:
        return scored_bullets  # 太少不需要重排

    # 智能跳过：分数分布足够分散时规则排序已足够好
    scores = [s.total_score for s in scored_bullets]
    score_spread = scores[0] - scores[-1] if scores else 0
    unique_scores = len(set(scores))
    if score_spread > 5.0 and unique_scores == len(scores):
        logger.info(
            f"跳过 LLM 重排序: 分数分布清晰 (spread={score_spread:.1f}, "
            f"unique={unique_scores}/{len(scores)})"
        )
        return scored_bullets

    llm = get_llm(temperature=0.1)

    # 构建 bullet 列表供 LLM 审阅
    bullet_lines = []
    for s in scored_bullets:
        ctx = get_bullet_context(s.bullet)
        bullet_lines.append(
            f"ID: {s.bullet.id}\n"
            f"  上下文: {ctx}\n"
            f"  原文: {s.bullet.text}\n"
            f"  匹配的技能: {', '.join(s.matched_skills) if s.matched_skills else '无'}\n"
            f"  当前分数: {s.total_score:.1f}\n"
        )

    prompt = f"""请根据以下 JD 要求，判断简历 bullets 的排序是否合理，并给出优化后的排序。

【目标岗位】{jd_position}
【JD 摘要】{jd_summary}

【当前排序的 Bullets（按分数从高到低）】
{chr(10).join(bullet_lines)}

请以 JSON 格式返回：
{{
  "bullet_ids_ordered": ["id1", "id2", ...],
  "reasoning": "排序调整的理由"
}}

注意：
1. 只需调整顺序，不要修改 bullet 内容
2. 优先排列与 JD 核心要求最相关的经历
3. 保持同一公司/项目的 bullets 尽量相邻
4. bullet_ids_ordered 中包含所有 bullet ID，不要遗漏

只返回 JSON。"""

    messages = [
        SystemMessage(content="你是一位资深技术招聘专家，精通简历筛选和排序。只返回 JSON。"),
        HumanMessage(content=prompt),
    ]

    response = llm.invoke(messages)
    content = response.content.strip()

    try:
        result = parse_and_validate(content, BulletReorderResult, context="Bullet 重排序")
    except LLMOutputError:
        logger.warning("LLM bullet 重排序失败，使用原始规则排序")
        return scored_bullets

    # 根据 LLM 建议的 ID 顺序重新排列
    id_to_bullet = {s.bullet.id: s for s in scored_bullets}
    reordered = []
    seen_ids = set()

    for bid in result.bullet_ids_ordered:
        if bid in id_to_bullet and bid not in seen_ids:
            reordered.append(id_to_bullet[bid])
            seen_ids.add(bid)

    # 补充未被 LLM 覆盖的 bullets
    for s in scored_bullets:
        if s.bullet.id not in seen_ids:
            reordered.append(s)

    logger.debug(f"LLM 重排序完成: {result.reasoning[:100]}")
    return reordered


def _partial_match(skill_name: str, text_lower: str) -> bool:
    """部分匹配：技能名中的关键词出现在文本中

    例如 skill_name="FastAPI" 匹配 text_lower="使用fastapi构建..."
    需要处理中英文混合的情况
    """
    # 直接子串匹配
    if skill_name in text_lower:
        return True
    # 对于多词技能名（如 "Spring Boot"），分别匹配每个词
    parts = skill_name.replace("-", " ").replace("_", " ").split()
    if len(parts) > 1:
        return all(part.lower() in text_lower for part in parts if len(part) > 2)
    return False
