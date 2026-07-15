"use client";

import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";
import type { MatchResult } from "@/lib/types";
import { MATCH_ICONS } from "@/lib/constants";

interface MatchDetailsProps {
  matchResults: MatchResult[];
}

export function MatchDetails({ matchResults }: MatchDetailsProps) {
  if (!matchResults || matchResults.length === 0) return null;

  return (
    <div className="mt-6">
      <Accordion>
        <AccordionItem value="match-details" className="border rounded-lg px-3">
          <AccordionTrigger className="hover:no-underline py-2">
            <span className="text-sm font-bold text-gray-900">
              🎯 匹配详情
            </span>
          </AccordionTrigger>
          <AccordionContent className="text-sm pb-3">
            <ul className="space-y-1.5">
              {matchResults.map((r, i) => (
                <li key={i} className="flex items-start gap-2">
                  <span className="mt-0.5 shrink-0">
                    {MATCH_ICONS[r.status] || "❓"}
                  </span>
                  <span>
                    <strong>{r.skill}</strong> ({r.status}) — {r.detail}
                  </span>
                </li>
              ))}
            </ul>
          </AccordionContent>
        </AccordionItem>
      </Accordion>
    </div>
  );
}
