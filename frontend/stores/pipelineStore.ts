/**
 * Zustand Pipeline Store — 动态步骤管理
 *
 * 步骤不再硬编码。pipeline_start 事件传入 agents 数组，
 * 前端据此动态初始化步骤状态。
 */

import { create } from "zustand";
import type { StepState, OptimizationResult, FactCheckReport, SSEStepAgent } from "@/lib/types";

// ===== Store 接口 =====

interface PipelineState {
  // 流水线生命周期
  pipelineRunning: boolean;
  pipelineDone: boolean;

  // 步骤状态（动态键：按 step 编号索引）
  steps: Record<number, StepState>;

  // Agent 元信息（从 SSE pipeline_start 获取）
  agentMeta: Record<string, SSEStepAgent>;

  // 最终结果
  result: OptimizationResult | null;

  // 错误
  errorMessage: string;

  // 事实核查
  factCheck: FactCheckReport | null;

  // 总步骤数
  totalSteps: number;

  // ===== Actions =====
  resetPipeline: () => void;
  setAllStepsRunning: (agents: SSEStepAgent[]) => void;
  setStepRunning: (step: number, message: string) => void;
  setStepComplete: (step: number, data: Record<string, unknown>) => void;
  setStepError: (step: number, message: string) => void;
  setPipelineDone: (data: OptimizationResult) => void;
  setErrorMessage: (msg: string) => void;
  setPipelineStopped: () => void;
}

// ===== 通用步骤详情生成 =====

function buildStepDetail(data: Record<string, unknown>): string {
  const parts: string[] = [];

  // 自动提取关键统计信息（不依赖具体步骤编号）
  for (const [key, value] of Object.entries(data)) {
    if (key.startsWith("_")) continue; // 跳过内部字段

    if (key === "jd_skills" && Array.isArray(value)) {
      parts.push(`提取 ${value.length} 个技能`);
    } else if (key === "jd_position" && typeof value === "string" && value) {
      parts.push(`岗位: ${value}`);
    } else if (key === "resume_sections" && typeof value === "object" && value) {
      const keys = Object.keys(value);
      if (keys.length > 0) parts.push(`简历段落: ${keys.join(", ")}`);
    } else if (key === "parsed_resume" && typeof value === "object" && value) {
      const parsed = value as Record<string, unknown>;
      const skills = Array.isArray(parsed.skills) ? parsed.skills.length : 0;
      const exp = Array.isArray(parsed.experience) ? parsed.experience.length : 0;
      parts.push(`技能数: ${skills}`);
      parts.push(`工作经历: ${exp} 条`);
    } else if (key === "match_results" && Array.isArray(value)) {
      const arr = value as Array<{ status: string }>;
      const matched = arr.filter((r) => r.status === "match").length;
      const missing = arr.filter((r) => r.status === "missing").length;
      const partial = arr.filter((r) => r.status === "partial_match").length;
      parts.push(`✅ 匹配: ${matched}`);
      parts.push(`❌ 缺失: ${missing}`);
    } else if (key === "overall_score" && typeof value === "number") {
      parts.push(`综合评分: ${(value * 100).toFixed(0)}%`);
    } else if (key === "suggestions" && Array.isArray(value)) {
      parts.push(`共 ${value.length} 条建议`);
    } else if (key === "fact_check" && typeof value === "object" && value) {
      const fc = value as Record<string, unknown>;
      if (typeof fc.overall_trust_score === "number") {
        parts.push(`可信度: ${(fc.overall_trust_score * 100).toFixed(0)}%`);
      }
    }
  }

  return parts.join(" | ");
}

// ===== 初始状态 =====

const initialState = {
  pipelineRunning: false,
  pipelineDone: false,
  steps: {} as Record<number, StepState>,
  agentMeta: {} as Record<string, SSEStepAgent>,
  result: null as OptimizationResult | null,
  errorMessage: "",
  factCheck: null as FactCheckReport | null,
  totalSteps: 0,
};

// ===== Store 创建 =====

export const usePipelineStore = create<PipelineState>((set) => ({
  ...initialState,

  resetPipeline: () =>
    set({
      ...initialState,
      steps: {},
      agentMeta: {},
    }),

  /**
   * pipeline_start 事件 — 动态初始化所有步骤
   */
  setAllStepsRunning: (agents: SSEStepAgent[]) =>
    set({
      steps: Object.fromEntries(
        agents.map((a) => [
          a.step,
          {
            status: "running" as const,
            title: `${a.icon} ${a.title}`,
            detail: `${a.icon} ${a.title} 执行中...`,
            data: {},
          },
        ])
      ),
      agentMeta: Object.fromEntries(agents.map((a) => [a.name, a])),
      pipelineRunning: true,
      totalSteps: agents.length,
    }),

  setStepRunning: (step: number, message: string) =>
    set((state) => {
      if (!state.steps[step]) return state;
      return {
        steps: {
          ...state.steps,
          [step]: {
            ...state.steps[step],
            status: "running",
            detail: message,
          },
        },
      };
    }),

  setStepComplete: (step: number, data: Record<string, unknown>) =>
    set((state) => {
      if (!state.steps[step]) return state;
      const detail = buildStepDetail(data);
      return {
        steps: {
          ...state.steps,
          [step]: {
            ...state.steps[step],
            status: "complete",
            detail,
            data,
          },
        },
      };
    }),

  setStepError: (step: number, message: string) =>
    set((state) => {
      if (!state.steps[step]) return state;
      return {
        steps: {
          ...state.steps,
          [step]: {
            ...state.steps[step],
            status: "error",
            detail: `❌ ${message}`,
          },
        },
      };
    }),

  setPipelineDone: (data: OptimizationResult) => {
    // 持久化到 sessionStorage，刷新页面后 Evaluation 可恢复
    try { sessionStorage.setItem("lastResult", JSON.stringify(data)); } catch {}
    set({
      pipelineDone: true,
      pipelineRunning: false,
      result: data,
      factCheck: data.fact_check || null,
    });
  },

  setErrorMessage: (msg: string) =>
    set({
      errorMessage: msg,
      pipelineRunning: false,
    }),

  setPipelineStopped: () =>
    set({
      pipelineRunning: false,
    }),
}));
