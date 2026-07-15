"use client";

import type { Badcase } from "@/lib/types";

interface DiagnosisPanelProps {
  badcases: Badcase[];
}

export function DiagnosisPanel({ badcases }: DiagnosisPanelProps) {
  const criticals = badcases.filter((b) => b.severity === "critical");
  const warnings = badcases.filter((b) => b.severity === "warning");
  const infos = badcases.filter((b) => b.severity === "info");

  if (badcases.length === 0) {
    return (
      <div className="bg-green-50 border border-green-200 rounded-lg p-4 text-sm text-green-700">
        ✅ 系统运行正常，未发现明显问题
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <h3 className="text-base font-bold text-gray-900">🔍 智能诊断</h3>

      {criticals.length > 0 && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-3">
          <p className="font-semibold text-red-700 text-sm">
            ❌ {criticals.length} 个严重问题
          </p>
          <ul className="mt-2 space-y-1">
            {criticals.map((bc, i) => (
              <li key={i} className="text-xs text-red-600">
                <strong>{bc.type}</strong>: {bc.detail.slice(0, 200)}
              </li>
            ))}
          </ul>
        </div>
      )}

      {warnings.length > 0 && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3">
          <p className="font-semibold text-yellow-700 text-sm">
            ⚠️ {warnings.length} 个警告
          </p>
          <ul className="mt-2 space-y-1">
            {warnings.map((bc, i) => (
              <li key={i} className="text-xs text-yellow-700">
                <strong>{bc.type}</strong>
                {bc.skill ? ` [${bc.skill}]` : ""}:{" "}
                {(bc.detail || bc.explanation || "").slice(0, 200)}
              </li>
            ))}
          </ul>
        </div>
      )}

      {infos.length > 0 && (
        <details className="bg-gray-50 border rounded-lg p-3">
          <summary className="font-semibold text-gray-700 text-sm cursor-pointer">
            ℹ️ {infos.length} 个提示
          </summary>
          <ul className="mt-2 space-y-1">
            {infos.map((bc, i) => (
              <li key={i} className="text-xs text-gray-600">
                <strong>{bc.type}</strong>
                {bc.skill ? ` [${bc.skill}]` : ""}:{" "}
                {bc.detail.slice(0, 200)}
              </li>
            ))}
          </ul>
        </details>
      )}
    </div>
  );
}
