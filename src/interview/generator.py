"""
面试题生成器 — 根据 JD 技能要求生成 10 道分类面试题
每道题含参考答案和追问。带重试机制确保可靠性。
"""

import json
import logging
from typing import List

from langchain_core.messages import HumanMessage, SystemMessage

from src.generation.llm import get_llm
from src.generation.output_validator import extract_json_from_text

logger = logging.getLogger("interview_generator")

INTERVIEW_PROMPT = """你是一个资深的 AI/大模型领域技术面试官。请根据【JD要求】和【待考察技能点】，生成具有针对性、深度和差异化的面试题。

# 题目设计原则（极其重要）
1. 严禁使用千篇一律的模板（如"请简述核心原理和最佳实践"）。每道题必须针对具体技能和JD场景定制。
2. 题目类型根据技能属性动态调整：
   - 理论与架构类（AI Agent/LangGraph/RAG/系统设计）：侧重场景设计、多智能体协同、长短期记忆折中、架构权衡。
   - 工具与工程类（PyTorch/Docker/FastAPI/数据库）：侧重具体参数设定、工程踩坑、性能调优、API 调用逻辑。
   - 软实力类（沟通/领导力/学习能力）：侧重具体业务冲突或 Badcase 归因分析的行为/情景题。
3. 参考答案必须是针对该题目的【具体要点】（3-5条），不是抽象概念名词。
4. 追问必须能进一步压测候选人深度，不是泛泛的"能举个例子吗"。

# 输出格式
严格输出一行 JSON（不要 markdown 代码块，不要任何解释性文字）：
{"questions":[{"category":"分类","skill":"技能名","question":"具体问题","answer_points":["要点1","要点2","要点3"],"follow_up":"深度追问"}],"preparation_tips":"备考建议"}

# 数量要求
- 技术基础 3题 + 系统设计 2题 + 项目经验 3题 + 行为面试 2题 = 共10题
- 优先对候选人薄弱技能出题"""


def generate_interview_questions(
    jd_skills: List[dict],
    jd_summary: str,
    jd_position: str = "",
    match_results: List[dict] = None,
) -> dict:
    """根据 JD 生成 10 道面试题"""
    # 提取核心技能
    core_skills = [s.get("name", "") for s in jd_skills if s.get("proficiency") == "required"]
    if not core_skills:
        core_skills = [s.get("name", "") for s in jd_skills[:5] if s.get("name")]

    weak_skills = []
    if match_results:
        weak_skills = [r["skill"] for r in match_results if r.get("status") in ("missing", "partial_match")]

    prompt = f"""目标岗位：{jd_position}
岗位摘要：{jd_summary}
核心技能：{', '.join(core_skills[:8]) if core_skills else '通用技术岗'}
候选人薄弱点（重点出题）：{', '.join(weak_skills[:5]) if weak_skills else '无'}

请严格按格式生成10道面试题。记住：每题必须针对具体技能定制，禁用模板化问题。"""

    # 尝试生成，失败时重试
    for attempt in range(3):
        temp = 0.3 if attempt == 0 else 0.0
        llm = get_llm(temperature=temp, max_tokens=4096)  # 10道题JSON约3000-4000 token
        messages = [
            SystemMessage(content=INTERVIEW_PROMPT),
            HumanMessage(content=prompt),
        ]
        response = llm.invoke(messages)
        content = response.content.strip()

        # 正则清洗：移除 markdown 代码块、前后缀
        content = extract_json_from_text(content)

        try:
            result = json.loads(content)
            questions = result.get("questions", [])
            if questions and len(questions) >= 5:
                logger.info(f"面试题生成成功: {len(questions)} 道 (尝试 {attempt+1})")
                return {
                    "questions": questions,
                    "preparation_tips": result.get("preparation_tips", ""),
                }
            else:
                logger.warning(f"面试题数量不足 ({len(questions)}), 重试...")
        except json.JSONDecodeError as e:
            logger.warning(f"面试题JSON解析失败 (尝试 {attempt+1}): {e}")

    # 三次都失败：返回降级结果
    logger.error("面试题生成全部失败，返回降级结果")
    return {
        "questions": _fallback_questions(core_skills, jd_position),
        "preparation_tips": "（自动生成的通用面试题，建议刷新重试）",
    }


def _fallback_questions(skills: List[str], position: str) -> List[dict]:
    """降级：无 LLM 依赖时生成合理的通用面试题"""
    questions = []
    categories = [
        ("技术基础", 3), ("系统设计", 2), ("项目经验", 3), ("行为面试", 2)
    ]
    skill_idx = 0
    for cat, count in categories:
        for i in range(count):
            skill = skills[skill_idx % len(skills)] if skills else position
            skill_idx += 1
            if cat == "技术基础":
                q = f"在{skill}的实际项目中，你遇到过最棘手的技术问题是什么？你是如何定位和解决的？"
                answers = ["具体问题场景和影响范围", "排查思路和定位方法", "最终解决方案和取舍理由", "事后总结和预防措施"]
            elif cat == "系统设计":
                q = f"如果要基于{skill}设计一个支持高并发和故障自愈的系统，你会如何考虑架构、容灾和监控？"
                answers = ["系统分层架构和数据流设计", "高可用的容灾和降级策略", "关键监控指标和告警阈值", "技术选型的权衡理由"]
            elif cat == "项目经验":
                q = f"请描述你在{skill}相关项目中推动的一项技术改进，以及你是如何评估改进效果的。"
                answers = ["改进前的痛点和量化指标", "方案选型和实施路径", "上线后的效果对比数据", "复盘和改进空间"]
            else:
                q = "请描述一次你在跨团队协作中推动技术决策的经历，遇到的主要阻力是什么，你是如何化解的？"
                answers = ["技术决策的背景和分歧点", "沟通策略和利益平衡方式", "最终达成的共识和执行结果", "后续复盘的经验教训"]
            questions.append({
                "category": cat,
                "skill": skill,
                "question": q,
                "answer_points": answers,
                "follow_up": "如果让你重新做一次，你会在哪些环节做出不同的选择？",
            })
    return questions
