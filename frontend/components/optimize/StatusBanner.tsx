"use client";

import { Progress } from "@/components/ui/progress";
import { Button } from "@/components/ui/button";
import { usePipelineStore } from "@/stores/pipelineStore";
import { RefreshCw } from "lucide-react";

interface StatusBannerProps {
  onRetry?: () => void;
}

export function StatusBanner({ onRetry }: StatusBannerProps) {
  const pipelineRunning = usePipelineStore((s) => s.pipelineRunning);
  const errorMessage = usePipelineStore((s) => s.errorMessage);
  const steps = usePipelineStore((s) => s.steps);
  const totalSteps = usePipelineStore((s) => s.totalSteps);

  if (!pipelineRunning && !errorMessage) return null;

  if (errorMessage) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-3 text-sm text-red-700">
        <p className="font-semibold">❌ 错误</p>
        <p className="mt-0.5 whitespace-pre-wrap">{errorMessage}</p>
        {onRetry && (
          <Button variant="outline" size="sm" className="mt-2 text-xs" onClick={onRetry}>
            <RefreshCw className="w-3 h-3 mr-1" /> 重试
          </Button>
        )}
      </div>
    );
  }

  const finished = Object.values(steps).filter(
    (s) => s.status === "complete" || s.status === "error"
  ).length;
  const total = totalSteps || 4;
  const progress = Math.round((finished / total) * 100);

  return (
    <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 text-sm text-blue-700">
      <p className="font-semibold">🔄 流水线运行中...</p>
      <p className="text-xs mt-0.5 text-blue-600">
        Agent 流水线执行中，每个步骤完成后会实时更新
      </p>
      <Progress value={progress} className="mt-2 h-1.5" />
      <p className="text-xs mt-1 text-blue-500">
        已完成 {finished}/{total} 个 Agent
      </p>
    </div>
  );
}
