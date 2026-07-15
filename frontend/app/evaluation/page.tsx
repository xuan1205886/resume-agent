"use client";

import { useEffect } from "react";
import { usePipelineStore } from "@/stores/pipelineStore";
import { useEvaluation } from "@/hooks/useEvaluation";
import { MetricsGrid } from "@/components/evaluation/MetricsGrid";
import { DiagnosisPanel } from "@/components/evaluation/DiagnosisPanel";
import type { OptimizationResult } from "@/lib/types";

export default function EvaluationPage() {
  const result = usePipelineStore((s) => s.result);
  const factCheck = usePipelineStore((s) => s.factCheck);
  const setPipelineDone = usePipelineStore((s) => s.setPipelineDone);
  const metrics = useEvaluation(result, factCheck);

  // 刷新后从 sessionStorage 恢复上次分析结果
  useEffect(() => {
    if (!result) {
      try {
        const saved = sessionStorage.getItem("lastResult");
        if (saved) setPipelineDone(JSON.parse(saved) as OptimizationResult);
      } catch {}
    }
  }, []);

  if (!result) {
    return (
      <div className="text-center py-20 text-gray-400">
        <div className="text-5xl mb-4">📊</div>
        <p className="text-lg font-semibold mb-2">暂无评估数据</p>
        <p className="text-sm">
          请先在「优化」Tab 中完成一次简历分析
        </p>
        <p className="text-sm">评估指标将在分析完成后自动生成</p>
      </div>
    );
  }

  return (
    <div>
      <h2 className="text-lg font-bold text-gray-900 mb-4">📊 评估指标</h2>
      <MetricsGrid metrics={metrics} />
      <DiagnosisPanel badcases={metrics.badcases} />
    </div>
  );
}
