"use client";

import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import type { AtsScore } from "@/lib/ats-parser";

interface AtsScoreCardProps {
  score: AtsScore;
}

const GRADE_COLORS: Record<string, string> = {
  "A+": "text-green-600",
  A: "text-green-600",
  B: "text-blue-600",
  C: "text-yellow-600",
  D: "text-orange-600",
  F: "text-red-600",
};

export function AtsScoreCard({ score }: AtsScoreCardProps) {
  const { total, grade, breakdown } = score;
  const gradeColor = GRADE_COLORS[grade] || "text-gray-600";

  const bars = [
    { label: "姓名", value: breakdown.nameScore, max: 20 },
    { label: "邮箱", value: breakdown.emailScore, max: 20 },
    { label: "电话", value: breakdown.phoneScore, max: 10 },
    { label: "章节", value: breakdown.sectionsScore, max: 15 },
    { label: "教育", value: breakdown.educationScore, max: 15 },
    { label: "经历", value: breakdown.experienceScore, max: 15 },
    { label: "技能", value: breakdown.skillsScore, max: 5 },
  ];

  return (
    <div className="border rounded-lg bg-white p-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="font-bold text-gray-900">📊 ATS 兼容性评分</h3>
        <Badge variant="outline" className={`text-lg font-bold ${gradeColor}`}>
          {total}/100 ({grade})
        </Badge>
      </div>

      <Progress
        value={total}
        className="h-2 mb-3"
        // 颜色随分数变化
        style={
          {
            "--progress-background":
              total >= 80 ? "#34a853" : total >= 60 ? "#f9ab00" : "#ea4335",
          } as React.CSSProperties
        }
      />

      <div className="space-y-1.5">
        {bars.map((bar) => {
          const pct = Math.round((bar.value / bar.max) * 100);
          return (
            <div key={bar.label} className="flex items-center gap-2 text-xs">
              <span className="w-8 text-gray-500">{bar.label}</span>
              <div className="flex-1 bg-gray-100 rounded-full h-1.5">
                <div
                  className={`h-1.5 rounded-full ${
                    pct >= 80
                      ? "bg-green-500"
                      : pct >= 50
                        ? "bg-yellow-500"
                        : "bg-red-500"
                  }`}
                  style={{ width: `${pct}%` }}
                />
              </div>
              <span className="w-12 text-right text-gray-500">
                {bar.value}/{bar.max}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
