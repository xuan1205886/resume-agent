"""
Multi-Agent Graph — 动态 DAG（从 AgentRegistry 自动推导）

并行模式：
  阶段1: 所有无依赖的 Agent 并行启动
  阶段2+: 后续 Agent 等待依赖完成后执行

串行模式（调试回退）：
  按注册顺序线性串行
"""

import logging
from typing import Optional

from langgraph.graph import END, START, StateGraph

from src.agent.state import AgentState, create_initial_state
from src.agent.registry import AgentRegistry
from src.config import get_config

logger = logging.getLogger("agent_graph")


# AGENT_META 现在从 Registry 动态生成（保持向后兼容的 dict 接口）
def _build_agent_meta() -> dict:
    """从 Registry 构建 AGENT_META dict（向后兼容）"""
    meta = {}
    for i, agent in enumerate(AgentRegistry.list_required()):
        meta[agent.name] = {
            "step": i + 1,
            "title": agent.title,
            "icon": agent.icon,
        }
    return meta


# 动态计算（在模块加载时调用一次）
AGENT_META = _build_agent_meta()


def build_graph(mode: str = "parallel") -> StateGraph:
    """从 AgentRegistry 动态构建 DAG 并编译

    Args:
        mode: "parallel" — 基于依赖关系的 DAG 执行（默认）
              "sequential" — 按注册顺序线性串行（调试回退用）

    并行模式的图结构由 AgentSpec.dependencies 自动推导：
      - 无依赖 → 从 START 出发，可并行
      - 有依赖 → 等待所有依赖完成后再执行
    """
    workflow = StateGraph(AgentState)

    # 从 Registry 获取所有必需节点
    nodes = AgentRegistry.get_graph_nodes()

    if mode == "sequential":
        logger.info(f"使用串行流水线模式（{len(nodes)} 个 Agent）")
        # 添加所有节点
        for name, node_fn in nodes:
            workflow.add_node(name, node_fn)

        # 线性连接
        prev_name = None
        for name, _ in nodes:
            if prev_name is None:
                workflow.set_entry_point(name)
            else:
                workflow.add_edge(prev_name, name)
            prev_name = name

        if prev_name:
            workflow.add_edge(prev_name, END)

    else:
        logger.info(f"使用并行流水线模式（{len(nodes)} 个 Agent）")
        # 添加所有节点
        for name, node_fn in nodes:
            workflow.add_node(name, node_fn)

        # 从 START 连接所有入口节点（无依赖的节点）
        entry_nodes = AgentRegistry.get_entry_nodes()
        for name in entry_nodes:
            workflow.add_edge(START, name)

        # 连接依赖边
        dep_edges = AgentRegistry.get_dependency_edges()
        for source, target in dep_edges:
            workflow.add_edge(source, target)

        # 找到最终节点（没有被其他节点依赖的节点）→ 连接到 END
        all_sources = {e[0] for e in dep_edges}
        all_targets = {e[1] for e in dep_edges}
        final_nodes = all_targets - all_sources
        if not final_nodes:
            # 如果所有节点都被依赖（环形？），取最后一个注册的节点
            final_nodes = {nodes[-1][0]} if nodes else set()

        for name in final_nodes:
            workflow.add_edge(name, END)

        # 安全检查：确保所有节点都有通往 END 的路径
        # 如果某个节点不在 entry_nodes 也不在 final_nodes 中，
        # 说明它既是中间节点 — 这由 dep_edges 保证

    return workflow.compile()


def _get_pipeline_mode() -> str:
    try:
        cfg = get_config()
        return cfg.agent.pipeline_mode
    except Exception:
        return "parallel"


_agent = build_graph(mode=_get_pipeline_mode())


def run_pipeline(
    jd_text: str = "",
    resume_text: str = "",
    resume_pdf_path: str = "",
    stream: bool = False,
):
    """运行完整的 Agent 简历优化流水线

    Agent 列表由 AgentRegistry 动态决定。
    """
    initial_state = create_initial_state(
        jd_text=jd_text,
        resume_text=resume_text,
        resume_pdf_path=resume_pdf_path,
    )

    if stream:
        return _agent.stream(initial_state, stream_mode="updates")
    else:
        return _agent.invoke(initial_state)
