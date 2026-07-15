"use client";

import { useState } from "react";
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { Suggestion } from "@/lib/types";
import { SEVERITY_CONFIG } from "@/lib/constants";

interface SuggestionListProps {
  suggestions: Suggestion[];
}

const INITIAL_SHOW = 8;

export function SuggestionList({ suggestions }: SuggestionListProps) {
  const [showAll, setShowAll] = useState(false);

  if (!suggestions || suggestions.length === 0) {
    return null;
  }

  const displayed = showAll ? suggestions : suggestions.slice(0, INITIAL_SHOW);
  const hidden = suggestions.length - INITIAL_SHOW;

  return (
    <div className="mt-6">
      <h2 className="text-lg font-bold text-gray-900 mb-3">
        💡 优化建议 ({suggestions.length})
      </h2>
      <Accordion multiple className="space-y-2">
        {displayed.map((s, i) => {
          const config = SEVERITY_CONFIG[s.severity] || SEVERITY_CONFIG.optional;
          return (
            <AccordionItem
              key={i}
              value={`suggestion-${i}`}
              className="border rounded-lg px-3"
            >
              <AccordionTrigger className="hover:no-underline py-2">
                <div className="flex items-center gap-2 text-sm text-left">
                  <Badge
                    variant={config.badgeVariant}
                    className="text-xs shrink-0"
                    style={
                      s.severity === "critical"
                        ? { backgroundColor: "#ea4335", color: "white" }
                        : undefined
                    }
                  >
                    {config.label}
                  </Badge>
                  <span className="text-gray-500 text-xs">
                    [{s.section}]
                  </span>
                  <span className="text-gray-800 truncate max-w-[400px]">
                    {s.suggestion.slice(0, 80)}...
                  </span>
                </div>
              </AccordionTrigger>
              <AccordionContent className="text-sm space-y-2 pb-3">
                <div>
                  <span className="font-semibold text-gray-600">原文片段:</span>
                  <p className="text-gray-500 mt-0.5">{s.original || "无"}</p>
                </div>
                <div>
                  <span className="font-semibold text-gray-600">修改建议:</span>
                  <p className="text-gray-800 mt-0.5">{s.suggestion}</p>
                </div>
                <div>
                  <span className="font-semibold text-gray-600">原因:</span>
                  <p className="text-gray-500 mt-0.5">{s.reason}</p>
                </div>
              </AccordionContent>
            </AccordionItem>
          );
        })}
      </Accordion>
      {!showAll && hidden > 0 && (
        <Button
          variant="ghost"
          size="sm"
          className="mt-2 text-xs text-blue-600"
          onClick={() => setShowAll(true)}
        >
          显示全部 {suggestions.length} 条建议（还有 {hidden} 条隐藏）
        </Button>
      )}
    </div>
  );
}
