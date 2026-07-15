"use client";

import { useState } from "react";
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Copy, Check } from "lucide-react";
import type { PromptEntry } from "@/lib/types";

interface PromptCardProps {
  prompt: PromptEntry;
  index: number;
}

export function PromptCard({ prompt, index }: PromptCardProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(prompt.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <Accordion>
      <AccordionItem
        value={`prompt-${index}`}
        className="border rounded-lg px-3"
      >
        <AccordionTrigger className="hover:no-underline py-2">
          <div className="flex items-center gap-2 text-sm text-left">
            <Badge variant="secondary" className="text-xs">
              {prompt.category}
            </Badge>
            <span className="font-semibold text-gray-800">{prompt.name}</span>
            <span className="text-gray-400 text-xs">({prompt.version})</span>
          </div>
        </AccordionTrigger>
        <AccordionContent className="text-sm pb-3 space-y-3">
          <div className="flex items-center gap-4 text-xs text-gray-500">
            <span>版本: {prompt.version}</span>
            <span>源码位置: {prompt.source_file}</span>
          </div>

          {prompt.changelog.length > 0 && (
            <div>
              <p className="font-semibold text-gray-600 text-xs mb-1">
                变更日志:
              </p>
              <ul className="list-disc list-inside text-xs text-gray-500 space-y-0.5">
                {prompt.changelog.map((log, i) => (
                  <li key={i}>{log}</li>
                ))}
              </ul>
            </div>
          )}

          <div className="relative">
            <Button
              variant="ghost"
              size="sm"
              className="absolute top-2 right-2 h-7 text-xs"
              onClick={handleCopy}
            >
              {copied ? (
                <>
                  <Check className="w-3 h-3 mr-1" /> 已复制
                </>
              ) : (
                <>
                  <Copy className="w-3 h-3 mr-1" /> 复制
                </>
              )}
            </Button>
            <pre className="bg-gray-900 text-gray-100 p-4 rounded-lg text-xs overflow-x-auto whitespace-pre-wrap">
              {prompt.content}
            </pre>
          </div>
        </AccordionContent>
      </AccordionItem>
    </Accordion>
  );
}
