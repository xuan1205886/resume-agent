"use client";

import { Button } from "@/components/ui/button";
import { RefreshCw } from "lucide-react";

export default function ErrorPage({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div className="text-center py-20">
      <div className="text-5xl mb-4">⚠️</div>
      <h2 className="text-lg font-bold text-gray-900 mb-2">页面加载失败</h2>
      <p className="text-sm text-gray-500 mb-4 max-w-md mx-auto">
        {error.message?.slice(0, 200) || "发生了未知错误"}
      </p>
      <Button onClick={reset} variant="outline" size="sm">
        <RefreshCw className="w-4 h-4 mr-1" />
        重试
      </Button>
    </div>
  );
}
