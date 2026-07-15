/**
 * 常量定义 — 步骤元数据、颜色配置、严重度映射
 */

import type { StepState } from "./types";

// ===== Agent 元信息和步骤状态 — 从 SSE pipeline_start 事件动态初始化 =====
// 不再硬编码 Agent 列表。参见 stores/pipelineStore.ts 的 setAllStepsRunning()

// ===== API 基础 URL =====
export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8765";

// ===== Material Design 色值 =====
export const COLORS = {
  blue: "#1a73e8",
  green: "#34a853",
  yellow: "#f9ab00",
  red: "#ea4335",
  gray50: "#fafafa",
  gray100: "#f8f9fa",
  gray200: "#e0e0e0",
  gray400: "#9aa0a6",
  gray600: "#5f6368",

  // 步骤卡片
  stepRunningBg: "#e8f0fe",
  stepRunningBorder: "#1a73e8",
  stepCompleteBg: "#e6f4ea",
  stepCompleteBorder: "#34a853",
  stepErrorBg: "#fce8e6",
  stepErrorBorder: "#ea4335",

  // 分数徽章
  scoreHighBg: "#e6f4ea",
  scoreHighText: "#1e8e3e",
  scoreMidBg: "#fef7e0",
  scoreMidText: "#f9ab00",
  scoreLowBg: "#fce8e6",
  scoreLowText: "#ea4335",
} as const;

// ===== 严重度配置 =====
export const SEVERITY_CONFIG = {
  critical: { color: COLORS.red, label: "严重", badgeVariant: "destructive" as const },
  recommended: { color: COLORS.yellow, label: "建议", badgeVariant: "secondary" as const },
  optional: { color: COLORS.green, label: "可选", badgeVariant: "outline" as const },
};

export const DRIFT_CONFIG = {
  none: { emoji: "✅", color: COLORS.green, label: "无漂移" },
  minor: { emoji: "⚠️", color: COLORS.yellow, label: "轻微" },
  major: { emoji: "❗", color: COLORS.red, label: "严重" },
  fabricated: { emoji: "🚫", color: COLORS.red, label: "虚构" },
};

// ===== 匹配状态图标 =====
export const MATCH_ICONS: Record<string, string> = {
  match: "✅",
  partial_match: "⚠️",
  missing: "❌",
  mismatch: "🔄",
};

// ===== 评估指标配置 =====
export const METRIC_DEFINITIONS = [
  { key: "jd_coverage", label: "JD 覆盖率", desc: "JD要求技能被简历覆盖的比例" },
  { key: "match_quality", label: "匹配质量", desc: "匹配分析有详细证据的比例" },
  { key: "fact_trust", label: "事实可信度", desc: "生成简历与原简历的事实一致性" },
  { key: "format_score", label: "格式完整度", desc: "输出简历包含标准章节的比例" },
] as const;

// ===== Prompt 分类 =====
export const PROMPT_CATEGORIES = ["全部", "system", "resume", "jd", "user"] as const;

// ===== Tab 导航 =====
export const NAV_TABS = [
  { label: "优化", href: "/optimize" },
  { label: "评估", href: "/evaluation" },
  { label: "ATS 解析", href: "/ats-parser" },
  { label: "Prompts", href: "/prompts" },
  { label: "历史", href: "/history" },
] as const;
