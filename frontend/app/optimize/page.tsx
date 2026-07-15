"use client";

import { useState, useCallback, useEffect, useRef } from "react";
import { JDInput } from "@/components/optimize/JDInput";
import { ResumeUpload } from "@/components/optimize/ResumeUpload";
import { ActionButtons } from "@/components/optimize/ActionButtons";
import { StepProgress } from "@/components/optimize/StepProgress";
import { MatchStats } from "@/components/optimize/MatchStats";
import { StatusBanner } from "@/components/optimize/StatusBanner";
import { SuggestionList } from "@/components/optimize/SuggestionList";
import { OptimizedResume } from "@/components/optimize/OptimizedResume";
import { FactCheckPanel } from "@/components/optimize/FactCheckPanel";
import { MatchDetails } from "@/components/optimize/MatchDetails";
import { ReviewPanel } from "@/components/review/ReviewPanel";
import { useOptimizePipeline } from "@/hooks/useOptimizePipeline";

export default function OptimizePage() {
  // 输入状态（本地，不需要持久化）
  const [jdText, setJdText] = useState("");
  const [resumeFile, setResumeFile] = useState<File | null>(null);

  // 流水线状态
  const {
    startPipeline,
    abort,
    pipelineRunning,
    pipelineDone,
    steps,
    result,
    errorMessage,
    factCheck,
    resetPipeline,
  } = useOptimizePipeline();

  // 按 Agent 名称动态查找步骤编号（不硬编码 "3"）
  const skillMatcherStep = Object.entries(steps).find(
    ([, s]) => s.title.toLowerCase().includes("skill matcher")
  );
  const skillMatcherStepNum = skillMatcherStep ? Number(skillMatcherStep[0]) : null;

  // 审查模式
  const [reviewMode, setReviewMode] = useState(false);

  // 内联校验错误（替代 alert）
  const [validationError, setValidationError] = useState("");

  // 处理 Streamlit 的 _should_run 模式：先渲染 running 状态，再发起请求
  const pendingRunRef = useRef(false);

  const handleStart = useCallback(() => {
    if (!jdText.trim()) {
      setValidationError("请粘贴职位描述 (JD)");
      return;
    }
    if (!resumeFile) {
      setValidationError("请上传简历 PDF 文件");
      return;
    }
    setValidationError("");
    // 先重置，然后在 useEffect 中发起请求
    resetPipeline();
    pendingRunRef.current = true;
  }, [jdText, resumeFile, resetPipeline]);

  // 实际发起请求（在状态更新后）
  useEffect(() => {
    if (pendingRunRef.current && !pipelineRunning && !pipelineDone) {
      pendingRunRef.current = false;
      startPipeline(jdText, resumeFile!);
    }
  }, [pipelineRunning, pipelineDone, jdText, resumeFile, startPipeline]);

  const handleReset = useCallback(() => {
    abort();
    resetPipeline();
    setJdText("");
    setResumeFile(null);
  }, [abort, resetPipeline]);

  const canStart = jdText.trim().length > 0 && resumeFile !== null;

  return (
    <div className="flex gap-6">
      {/* ===== 左栏：输入区 ===== */}
      <div className="w-[40%] shrink-0 space-y-4">
        <h2 className="text-base font-bold text-gray-900">📥 输入</h2>

        <JDInput
          value={jdText}
          onChange={setJdText}
          disabled={pipelineRunning}
        />

        <ResumeUpload
          file={resumeFile}
          onFileChange={(f) => { setResumeFile(f); setValidationError(""); }}
          disabled={pipelineRunning}
        />

        {validationError && (
          <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
            ⚠️ {validationError}
          </p>
        )}

        <ActionButtons
          onStart={handleStart}
          onReset={handleReset}
          disabled={pipelineRunning}
          canStart={canStart}
        />

        <StatusBanner onRetry={handleStart} />
      </div>

      {/* ===== 右栏：进度 + 结果 ===== */}
      <div className="flex-1 min-w-0">
        <h2 className="text-base font-bold text-gray-900 mb-4">📊 执行进度</h2>

        <StepProgress />

        {/* Skill Matcher 完成后显示匹配统计（按名称动态查找） */}
        {skillMatcherStepNum && steps[skillMatcherStepNum]?.status === "complete" && steps[skillMatcherStepNum]?.data && (
          <MatchStats data={steps[skillMatcherStepNum].data} />
        )}

        {/* ===== 结果展示 ===== */}
        {pipelineDone && result && (
          <div className="mt-6 space-y-2">
            <SuggestionList suggestions={result.suggestions || []} />

            {/* 审查模式切换 */}
            <div className="flex items-center gap-2">
              <button
                onClick={() => setReviewMode(!reviewMode)}
                className={`text-xs px-3 py-1 rounded-full border transition-colors ${
                  reviewMode
                    ? "bg-blue-100 border-blue-300 text-blue-700"
                    : "bg-gray-100 border-gray-200 text-gray-500"
                }`}
              >
                {reviewMode ? "🔍 审查模式" : "📝 预览模式"}
              </button>
              <span className="text-xs text-gray-400">
                {reviewMode ? "逐条审查 AI 修改" : "直接查看最终简历"}
              </span>
            </div>

            {/* 审查面板 */}
            {reviewMode && (
              <ReviewPanel
                result={result}
                onReviewComplete={() => {}}
              />
            )}

            {/* 优化版简历（非审查模式下显示，或审查模式下也在底部显示） */}
            <OptimizedResume markdown={result.optimized_resume_md || ""} />
            <FactCheckPanel factCheck={factCheck} />
            <MatchDetails matchResults={result.match_results || []} />
          </div>
        )}
      </div>
    </div>
  );
}
