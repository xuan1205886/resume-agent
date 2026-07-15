"use client";

import { Loader2, CheckCircle2, XCircle, Circle } from "lucide-react";
import type { StepStatus } from "@/lib/types";

interface StepCardProps {
  step: number;
  status: StepStatus;
  title: string;
  detail: string;
}

const statusConfig: Record<
  StepStatus,
  { icon: React.ReactNode; className: string }
> = {
  pending: {
    icon: <Circle className="w-5 h-5 text-gray-300" />,
    className: "border-gray-200 bg-gray-50",
  },
  running: {
    icon: <Loader2 className="w-5 h-5 text-blue-500 animate-spin" />,
    className: "border-l-4 border-l-blue-500 bg-blue-50",
  },
  complete: {
    icon: <CheckCircle2 className="w-5 h-5 text-green-500" />,
    className: "border-l-4 border-l-green-500 bg-green-50",
  },
  error: {
    icon: <XCircle className="w-5 h-5 text-red-500" />,
    className: "border-l-4 border-l-red-500 bg-red-50",
  },
};

export function StepCard({ step, status, title, detail }: StepCardProps) {
  const config = statusConfig[status];

  return (
    <div
      className={`rounded-lg border p-3 mb-2 transition-colors ${config.className}`}
    >
      <div className="flex items-center gap-2">
        {config.icon}
        <span className="font-semibold text-sm text-gray-800">{title}</span>
      </div>
      {detail && (
        <p className="text-xs text-gray-500 mt-1.5 ml-7">{detail}</p>
      )}
    </div>
  );
}
