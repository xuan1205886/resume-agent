"use client";

import { usePipelineStore } from "@/stores/pipelineStore";
import { StepCard } from "./StepCard";

export function StepProgress() {
  const steps = usePipelineStore((s) => s.steps);
  const totalSteps = usePipelineStore((s) => s.totalSteps);

  const allPending = Object.values(steps).every(
    (s) => s.status === "pending"
  );

  if (allPending) {
    return (
      <div className="text-center py-12 text-gray-400">
        <p className="text-lg">等待开始...</p>
        <p className="text-sm mt-1">
          在左侧粘贴JD并上传简历后点击「开始优化」
        </p>
      </div>
    );
  }

  const stepCount = totalSteps || Object.keys(steps).length || 4;

  return (
    <div>
      {Array.from({ length: stepCount }, (_, i) => i + 1).map((stepNum) => (
        <StepCard
          key={stepNum}
          step={stepNum}
          status={steps[stepNum]?.status || "pending"}
          title={steps[stepNum]?.title || `Step ${stepNum}`}
          detail={steps[stepNum]?.detail || ""}
        />
      ))}
    </div>
  );
}
