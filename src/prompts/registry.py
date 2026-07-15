"""
Prompt 注册表 — 全局 Prompts 的版本管理和展示
"""

from dataclasses import dataclass, field
from typing import List


@dataclass
class PromptEntry:
    """一个 Prompt 条目"""
    name: str              # 名称
    category: str          # 分类：system/user/jd/resume
    version: str           # 版本号
    content: str           # Prompt 内容
    source_file: str = ""  # 源码文件位置
    changelog: List[str] = field(default_factory=list)  # 变更日志


# 全局 Prompt 注册表
PROMPT_REGISTRY: List[PromptEntry] = [
    PromptEntry(
        name="JD Analyzer System Prompt",
        category="system",
        version="v2.0",
        content="""你是一位资深技术招聘专家。请分析以下职位描述(JD)，提取结构化信息。
以 JSON 格式返回：position, company, summary, responsibilities, skills[], education, experience_years。
skills 每项包含 name, category(hard/soft/tool/domain), proficiency(required/preferred/nice-to-have)。""",
        changelog=["v2.0: 增加 proficiency 分级", "v1.0: 初始版本"],
        source_file="src/parsing/jd_parser.py — JD_PARSE_PROMPT",
    ),
    PromptEntry(
        name="Resume Parser System Prompt",
        category="resume",
        version="v2.0",
        content="""你是一位专业的简历解析专家。将PDF提取的简历文本解析为结构化段落。
以 JSON 格式返回：contact, summary, skills[], experience[], education[], projects[]。
注意：只提取原文中实际存在的信息，不要编造。""",
        changelog=["v2.0: 增加 projects 字段", "v1.0: 初始版本"],
        source_file="src/parsing/resume_parser.py — RESUME_PARSE_PROMPT",
    ),
    PromptEntry(
        name="Skill Matcher System Prompt",
        category="system",
        version="v2.1",
        content="""你是一位资深技术招聘专家。对比 JD 要求的技能和候选人简历中实际展示的技能。
返回 match_results[] (每项含 skill, status, score, detail), match_summary, overall_score。
判断标准：match(明确展示), partial_match(有但不够), missing(完全没有), mismatch(方向不匹配)。""",
        changelog=["v2.1: 增加 mismatch 状态", "v2.0: 增加 KB 参考上下文", "v1.0: 初始版本"],
        source_file="src/matching/skill_matcher.py — MATCH_ANALYSIS_PROMPT",
    ),
    PromptEntry(
        name="Resume Optimizer Assembly Prompt",
        category="resume",
        version="v3.0",
        content="""你是顶级简历写作专家。核心原则：事实保留优先，只能基于原始 Bullets 润色，不编造新技术/工具/数字。
允许：STAR格式改写、措辞优化、结构整理、合理裁剪。
禁止：添加原文没有的技术名词、编造量化数据、改变公司名/职位/时间。
输出格式：Markdown，标准英文标题 Summary/Skills/Experience/Education/Projects。""",
        changelog=["v3.0: 块级组装模式，增加严格事实约束", "v2.0: 增加 ATS 优化", "v1.0: 初始全文本重写"],
        source_file="src/optimization/resume_writer.py — ASSEMBLY_PROMPT",
    ),
    PromptEntry(
        name="Fact Check System Prompt",
        category="system",
        version="v1.0",
        content="""你是严谨的简历审计专家。逐条对比优化版和原始简历的 bullet。
判断漂移等级：none(完全一致)、minor(轻微改写)、major(新增原文没有的事实)、fabricated(完全编造)。
特别警惕：原文没有的技术/工具、原文没有的量化数字、改变公司名/职位/时间、凭空编造新经历。""",
        changelog=["v1.0: 初始版本"],
    ),
    PromptEntry(
        name="Suggestion Generator System Prompt",
        category="system",
        version="v2.0",
        content="""你是资深简历优化顾问。分析候选人简历与目标岗位差距，生成优化建议。
每项建议含：section, severity(critical/recommended/optional), original, suggestion, reason。
优化原则：STAR法则、量化成就、动作动词、关键词匹配、ATS友好、诚实原则。""",
        changelog=["v2.0: 增加诚实原则约束", "v1.0: 初始版本"],
    ),
]


def get_prompts_by_category(category: str = "") -> List[PromptEntry]:
    """按分类筛选 Prompt"""
    if not category:
        return PROMPT_REGISTRY
    return [p for p in PROMPT_REGISTRY if p.category == category]
