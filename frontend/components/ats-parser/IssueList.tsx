"use client";

import type { AtsIssue } from "@/lib/ats-parser";

interface IssueListProps {
  issues: AtsIssue[];
}

const ICONS: Record<string, string> = {
  error: "❌",
  warning: "⚠️",
  info: "ℹ️",
};

const COLORS: Record<string, string> = {
  error: "border-red-200 bg-red-50 text-red-700",
  warning: "border-yellow-200 bg-yellow-50 text-yellow-700",
  info: "border-blue-200 bg-blue-50 text-blue-700",
};

export function IssueList({ issues }: IssueListProps) {
  if (issues.length === 0) {
    return (
      <div className="border border-green-200 bg-green-50 rounded-lg p-3 text-sm text-green-700">
        ✅ 未发现 ATS 可读性问题。你的简历 ATS 兼容性良好！
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <h4 className="text-sm font-semibold text-gray-700">
        ⚠️ 发现 {issues.length} 个问题
      </h4>
      {issues.map((issue, i) => (
        <div
          key={i}
          className={`border rounded-lg p-2.5 text-xs ${COLORS[issue.severity]}`}
        >
          <span className="font-semibold">
            {ICONS[issue.severity]} [{issue.category}]
          </span>{" "}
          {issue.message}
        </div>
      ))}
    </div>
  );
}
