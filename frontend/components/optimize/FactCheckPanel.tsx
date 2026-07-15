"use client";

import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";
import type { FactCheckReport } from "@/lib/types";
import { DRIFT_CONFIG } from "@/lib/constants";

interface FactCheckPanelProps {
  factCheck: FactCheckReport | null;
}

export function FactCheckPanel({ factCheck }: FactCheckPanelProps) {
  if (!factCheck || !factCheck.verdicts || factCheck.verdicts.length === 0) {
    return null;
  }

  const trustScore = factCheck.overall_trust_score || 0;
  const trustColor =
    trustScore >= 0.9
      ? "text-green-600"
      : trustScore >= 0.7
        ? "text-yellow-600"
        : "text-red-600";

  return (
    <div className="mt-6">
      <Accordion>
        <AccordionItem value="fact-check" className="border rounded-lg px-3">
          <AccordionTrigger className="hover:no-underline py-2">
            <span className="text-sm font-bold text-gray-900">
              🛡️ 事实核查 (Fact-Drift Check)
            </span>
          </AccordionTrigger>
          <AccordionContent className="text-sm pb-3 space-y-3">
            {/* 整体可信度 */}
            <div className="bg-gray-50 rounded-lg p-3">
              <span className={`text-lg font-bold ${trustColor}`}>
                整体可信度: {(trustScore * 100).toFixed(0)}%
              </span>
              <span className="text-gray-500 ml-3 text-xs">
                ✅ 无漂移: {factCheck.none_count || 0} |
                ⚠️ 轻微: {factCheck.minor_count || 0} |
                ❗ 严重: {factCheck.major_count || 0} |
                🚫 虚构: {factCheck.fabricated_count || 0}
              </span>
              {factCheck.summary && (
                <p className="text-gray-500 mt-1 text-xs">
                  💬 {factCheck.summary}
                </p>
              )}
            </div>

            {/* 详细 Verdicts */}
            {factCheck.verdicts.slice(0, 10).map((v, i) => {
              const config = DRIFT_CONFIG[v.drift_level] || DRIFT_CONFIG.none;
              return (
                <Accordion
                  key={i}
                  className="border rounded"
                >
                  <AccordionItem value={`verdict-${i}`}>
                    <AccordionTrigger className="hover:no-underline py-2 px-3 text-xs">
                      <span>
                        {config.emoji} [{config.label}]{" "}
                        {(v.generated_text || "").slice(0, 80)}...
                      </span>
                    </AccordionTrigger>
                    <AccordionContent className="px-3 pb-2 text-xs space-y-1.5">
                      <div>
                        <span className="font-semibold">生成文本:</span>
                        <p className="text-gray-700 mt-0.5">
                          {v.generated_text}
                        </p>
                      </div>
                      <div>
                        <span className="font-semibold">原文对照:</span>
                        <p className="text-gray-500 mt-0.5">
                          {v.original_text || "(无对应原文)"}
                        </p>
                      </div>
                      <div>
                        <span className="font-semibold">判断:</span>
                        <p className="text-gray-700 mt-0.5">
                          {v.explanation}
                        </p>
                      </div>
                      {v.added_facts && v.added_facts.length > 0 && (
                        <div>
                          <span className="font-semibold text-red-600">
                            ➕ 新增事实:
                          </span>
                          <span className="text-red-500">
                            {" "}
                            {v.added_facts.join(", ")}
                          </span>
                        </div>
                      )}
                      {v.missing_facts && v.missing_facts.length > 0 && (
                        <div>
                          <span className="font-semibold text-yellow-600">
                            ⚠️ 丢失事实:
                          </span>
                          <span className="text-yellow-600">
                            {" "}
                            {v.missing_facts.join(", ")}
                          </span>
                        </div>
                      )}
                    </AccordionContent>
                  </AccordionItem>
                </Accordion>
              );
            })}
          </AccordionContent>
        </AccordionItem>
      </Accordion>
    </div>
  );
}
