"""
Agent 注册表 — 所有 Agent 的唯一真相来源

新增 Agent 只需在这里注册，Graph、SSE、前端自动适配。
"""

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple


@dataclass
class AgentSpec:
    """单个 Agent 的完整规格声明"""

    name: str                              # 唯一标识 "jd_analyzer"
    title: str                             # 显示名称 "JD Analyzer Agent"
    icon: str                              # 图标 emoji
    node_fn: Callable                      # 节点函数
    tools: List[Any] = field(default_factory=list)   # Tool 实例列表
    input_fields: List[str] = field(default_factory=list)   # 从 state 读取的字段
    output_fields: List[str] = field(default_factory=list)  # 写入 state 的字段
    dependencies: List[str] = field(default_factory=list)   # 依赖的 Agent 名称列表
    optional: bool = False                 # 失败时是否跳过（不阻塞流水线）


class AgentRegistry:
    """中央 Agent 注册表（类级单例模式）"""

    _agents: Dict[str, AgentSpec] = {}
    _order: List[str] = []  # 注册顺序（决定 step 编号）

    # ═══════════════════════════════════════════════
    # 注册
    # ═══════════════════════════════════════════════

    @classmethod
    def register(cls, spec: AgentSpec) -> None:
        """注册一个 Agent"""
        cls._agents[spec.name] = spec
        cls._order.append(spec.name)

    @classmethod
    def clear(cls) -> None:
        """清空注册表（仅测试用）"""
        cls._agents.clear()
        cls._order.clear()

    # ═══════════════════════════════════════════════
    # 查询
    # ═══════════════════════════════════════════════

    @classmethod
    def get(cls, name: str) -> Optional[AgentSpec]:
        """按名称获取 Agent"""
        return cls._agents.get(name)

    @classmethod
    def list_all(cls) -> List[AgentSpec]:
        """列出所有已注册的 Agent（按注册顺序）"""
        return [cls._agents[name] for name in cls._order if name in cls._agents]

    @classmethod
    def list_required(cls) -> List[AgentSpec]:
        """列出必需执行的 Agent（optional=False）"""
        return [a for a in cls.list_all() if not a.optional]

    # ═══════════════════════════════════════════════
    # Graph 层使用
    # ═══════════════════════════════════════════════

    @classmethod
    def get_graph_nodes(cls) -> List[Tuple[str, Callable]]:
        """返回 [(name, node_fn), ...] 供 graph.add_node() 使用"""
        return [(a.name, a.node_fn) for a in cls.list_required()]

    @classmethod
    def get_dependency_edges(cls) -> List[Tuple[str, str]]:
        """返回 [(source, target), ...] 边列表

        每个 Agent 的 dependencies 字段表示"我需要这些 Agent 先完成"，
        因此生成 edges: dep → agent（每个依赖产生一条边）
        """
        edges = []
        for agent in cls.list_required():
            for dep in agent.dependencies:
                if dep in cls._agents:
                    edges.append((dep, agent.name))
        return edges

    @classmethod
    def get_entry_nodes(cls) -> List[str]:
        """返回无依赖的入口节点名称列表（从 START 出发）"""
        entry = []
        required = {a.name for a in cls.list_required()}
        for agent in cls.list_required():
            has_dep = any(d in required for d in agent.dependencies)
            if not has_dep:
                entry.append(agent.name)
        return entry

    # ═══════════════════════════════════════════════
    # API / SSE 层使用
    # ═══════════════════════════════════════════════

    @classmethod
    def get_meta_for_sse(cls) -> List[dict]:
        """返回 SSE pipeline_start 所需的 agents 数组"""
        return [
            {
                "step": i + 1,
                "name": a.name,
                "title": a.title,
                "icon": a.icon,
            }
            for i, a in enumerate(cls.list_required())
        ]

    @classmethod
    def get_all_output_fields(cls) -> List[str]:
        """合并所有 Agent 的 output_fields（用于 _build_done_data）"""
        fields = []
        seen = set()
        for agent in cls.list_all():  # 包含 optional
            for f in agent.output_fields:
                if f not in seen:
                    fields.append(f)
                    seen.add(f)
        return fields

    @classmethod
    def find_agent_by_step(cls, step: int) -> Optional[AgentSpec]:
        """按 SSE step 编号查找 Agent"""
        agents = cls.list_required()
        if 1 <= step <= len(agents):
            return agents[step - 1]
        return None

    @classmethod
    def total_steps(cls) -> int:
        """必需执行的 Agent 总数"""
        return len(cls.list_required())


# ═══════════════════════════════════════════════
# 注册所有 6 个 Agent
# ═══════════════════════════════════════════════

def _register_all_agents():
    """在模块加载时注册所有 Agent（延迟导入避免循环依赖）"""
    from src.agent.nodes import (
        node_jd_analyzer,
        node_resume_parser,
        node_skill_matcher,
        node_resume_optimizer,
    )
    from src.agent.tools import (
        JDParserTool,
        ResumeParserTool,
        SkillMatchTool,
        BulletScoreTool,
        FactCheckTool,
    )

    # Agent 1: JD Analyzer — 无依赖，入口节点
    AgentRegistry.register(AgentSpec(
        name="jd_analyzer",
        title="JD Analyzer Agent",
        icon="🔍",
        node_fn=node_jd_analyzer,
        tools=[JDParserTool()],
        input_fields=["jd_text"],
        output_fields=["jd_parsed", "jd_skills", "jd_summary", "jd_position"],
        dependencies=[],
    ))

    # Agent 2: Resume Parser — 无依赖，入口节点（与 JD Analyzer 并行）
    AgentRegistry.register(AgentSpec(
        name="resume_parser",
        title="Resume Parser Agent",
        icon="📄",
        node_fn=node_resume_parser,
        tools=[ResumeParserTool()],
        input_fields=["resume_text", "resume_pdf_path"],
        output_fields=["parsed_resume", "resume_sections", "resume_text"],
        dependencies=[],
    ))

    # Agent 3: Skill Matcher — 依赖 JD Analyzer 和 Resume Parser
    AgentRegistry.register(AgentSpec(
        name="skill_matcher",
        title="Skill Matcher Agent",
        icon="🎯",
        node_fn=node_skill_matcher,
        tools=[SkillMatchTool()],
        input_fields=["jd_skills", "resume_sections", "jd_summary"],
        output_fields=["match_results", "match_summary", "overall_score", "missing_skills"],
        dependencies=["jd_analyzer", "resume_parser"],
    ))

    # Agent 4: Resume Optimizer — 依赖 Skill Matcher
    AgentRegistry.register(AgentSpec(
        name="resume_optimizer",
        title="Resume Optimizer Agent",
        icon="✨",
        node_fn=node_resume_optimizer,
        tools=[BulletScoreTool(), FactCheckTool()],
        input_fields=["jd_summary", "jd_position", "jd_skills", "resume_sections", "parsed_resume", "match_results"],
        output_fields=["suggestions", "overall_advice", "optimized_resume_md", "fact_check", "selected_bullets_count", "total_bullets_count", "scored_bullets"],
        dependencies=["skill_matcher"],
    ))



# 模块加载时自动注册
_register_all_agents()
