"use client";

import { Button } from "@/components/ui/button";
import { Play, RotateCcw } from "lucide-react";

interface ActionButtonsProps {
  onStart: () => void;
  onReset: () => void;
  disabled: boolean;
  canStart: boolean;
}

export function ActionButtons({
  onStart,
  onReset,
  disabled,
  canStart,
}: ActionButtonsProps) {
  return (
    <div className="flex gap-2">
      <Button
        onClick={onStart}
        disabled={disabled || !canStart}
        className="flex-1 bg-blue-600 hover:bg-blue-700 text-white"
      >
        <Play className="w-4 h-4 mr-1" />
        开始优化
      </Button>
      <Button onClick={onReset} variant="outline" disabled={disabled}>
        <RotateCcw className="w-4 h-4 mr-1" />
        重置
      </Button>
    </div>
  );
}
