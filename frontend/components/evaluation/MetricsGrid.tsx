"use client";

import { MetricCard } from "./MetricCard";
import type { EvaluationMetrics } from "@/lib/types";
import { METRIC_DEFINITIONS } from "@/lib/constants";

interface MetricsGridProps {
  metrics: EvaluationMetrics;
}

export function MetricsGrid({ metrics }: MetricsGridProps) {
  return (
    <div className="grid grid-cols-4 gap-3 mb-6">
      {METRIC_DEFINITIONS.map((def) => {
        const value = metrics[def.key as keyof EvaluationMetrics] as number;
        return (
          <MetricCard
            key={def.key}
            label={def.label}
            value={
              def.key === "fact_trust" && (value === 0 || value === -1)
                ? "N/A"
                : value
            }
            description={def.desc}
            isNA={def.key === "fact_trust" && (value === 0 || value === -1)}
          />
        );
      })}
    </div>
  );
}
