"use client";

import { Textarea } from "@/components/ui/textarea";

interface JDInputProps {
  value: string;
  onChange: (value: string) => void;
  disabled: boolean;
}

export function JDInput({ value, onChange, disabled }: JDInputProps) {
  return (
    <div>
      <label className="text-sm font-semibold text-gray-700 mb-1.5 block">
        📋 职位描述 (JD)
      </label>
      <Textarea
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder="粘贴目标岗位的职位描述...&#10;&#10;例如：&#10;我们正在寻找一位AI应用开发工程师...&#10;&#10;岗位要求：&#10;1. 精通 Python 和 FastAPI&#10;2. 熟悉 LangChain/LangGraph&#10;3. 有 RAG 系统开发经验..."
        className="min-h-[200px] resize-y"
        disabled={disabled}
      />
    </div>
  );
}
