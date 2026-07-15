/**
 * TypeScript 类型定义 — 对应后端 Pydantic schemas
 */

// ===== SSE 事件 =====
export interface SSEStepAgent {
  step: number;
  name: string;
  title: string;
  icon: string;
}

export interface SSEEvent {
  type: "pipeline_start" | "step_start" | "step_complete" | "step_error" | "done" | "error";
  step: number;
  node: string;
  data: Record<string, unknown>;
  message: string;
}

// ===== 步骤状态 =====
export type StepStatus = "pending" | "running" | "complete" | "error";

export interface StepState {
  status: StepStatus;
  title: string;
  detail: string;
  data: Record<string, unknown>;
}

// ===== 技能匹配 =====
export type MatchStatus = "match" | "partial_match" | "missing" | "mismatch";

export interface MatchResult {
  skill: string;
  status: MatchStatus;
  score: number;
  detail: string;
}

// ===== 优化建议 =====
export type SuggestionSeverity = "critical" | "recommended" | "optional";

export interface Suggestion {
  section: string;
  severity: SuggestionSeverity;
  original: string;
  suggestion: string;
  reason: string;
}

// ===== 审查状态 =====
export type ReviewStatus = "pending" | "accepted" | "rejected" | "edited";

// ===== 事实核查 =====
export type DriftLevel = "none" | "minor" | "major" | "fabricated";

export interface FactCheckVerdict {
  id: string;
  bullet_id: string;
  drift_level: DriftLevel;
  generated_text: string;
  original_text: string;
  explanation: string;
  added_facts?: string[];
  missing_facts?: string[];
}

export interface FactCheckReport {
  overall_trust_score: number;
  none_count: number;
  minor_count: number;
  major_count: number;
  fabricated_count: number;
  summary: string;
  verdicts: FactCheckVerdict[];
}

// ===== Bullet 评分 (前端审查面板用) =====

export interface BulletItem {
  id: string;
  text: string;
  source_type: string;
  company: string;
  title: string;
}

export interface BulletScore {
  id: string;
  text: string;
  source_type: string;
  company: string;
  title: string;
  total_score: number;
  matched_skills: string[];
}

// ===== 优化结果 (done 事件 data) =====
export interface OptimizationResult {
  optimized_resume_md: string;
  jd_skills: Record<string, unknown>[];
  jd_summary: string;
  jd_position: string;
  match_results: MatchResult[];
  match_summary: string;
  overall_score: number;
  suggestions: Suggestion[];
  overall_advice: string;
  fact_check: FactCheckReport;
  parsed_resume: Record<string, unknown>;
  resume_sections: Record<string, string>;
  selected_bullets_count: number;
  total_bullets_count: number;
  scored_bullets?: BulletScore[];
  interview_questions?: Record<string, unknown>[];
  interview_summary?: string;
  learning_plan_md?: string;
}

// ===== 评估指标 =====
export type BadcaseSeverity = "critical" | "warning" | "info";

export interface Badcase {
  type: string;
  severity: BadcaseSeverity;
  detail: string;
  explanation?: string;
  skill?: string;
}

export interface EvaluationMetrics {
  jd_coverage: number;
  match_quality: number;
  fact_trust: number;
  format_score: number;
  badcases: Badcase[];
}

// ===== Prompt 条目 =====
export interface PromptEntry {
  name: string;
  category: string;
  version: string;
  content: string;
  source_file: string;
  changelog: string[];
}

// ===== 历史记录 =====
export interface HistoryRecord {
  id: number;
  created_at: string;
  jd_position: string;
  overall_score: number;
}

export interface HistoryDetail {
  id: number;
  created_at: string;
  jd_text: string;
  jd_position: string;
  jd_summary: string;
  overall_score: number;
  optimized_resume_md: string;
  match_results_json: string;
  suggestions_json: string;
  fact_check_json: string;
  interview_questions_json: string;
  learning_plan_md: string;
  parsed_resume?: Record<string, unknown>;
  resume_sections?: Record<string, string>;
}

// ===== API 响应 =====
export interface HealthResponse {
  status: string;
  version: string;
}
