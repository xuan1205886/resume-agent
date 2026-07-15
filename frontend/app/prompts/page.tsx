"use client";

import { useState } from "react";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { PromptCard } from "@/components/prompts/PromptCard";
import { PROMPT_REGISTRY, getPromptsByCategory } from "@/lib/promptData";
import { PROMPT_CATEGORIES } from "@/lib/constants";

export default function PromptsPage() {
  const [category, setCategory] = useState("全部");
  const prompts = getPromptsByCategory(category);

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-lg font-bold text-gray-900">📝 Prompt Design</h2>
          <p className="text-xs text-gray-500 mt-0.5">
            管理所有 Agent 的 System/User Prompt，支持版本追踪和变更日志
          </p>
        </div>
        <Select value={category} onValueChange={(v) => setCategory(v || "全部")}>
          <SelectTrigger className="w-[140px]">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {PROMPT_CATEGORIES.map((cat) => (
              <SelectItem key={cat} value={cat}>
                {cat}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {prompts.length === 0 ? (
        <p className="text-center py-12 text-gray-400">该分类下暂无 Prompt</p>
      ) : (
        <div className="space-y-3">
          {prompts.map((prompt, i) => (
            <PromptCard key={`${prompt.name}-${i}`} prompt={prompt} index={i} />
          ))}
        </div>
      )}
    </div>
  );
}
