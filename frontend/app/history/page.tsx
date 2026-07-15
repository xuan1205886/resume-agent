"use client";

import { useState, useMemo } from "react";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { RecordDetail } from "@/components/history/RecordDetail";
import { useHistoryList, useHistoryDetail } from "@/hooks/useHistory";

export default function HistoryPage() {
  const { data: records, isLoading, isError } = useHistoryList(50);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const { data: detail, isLoading: isLoadingDetail } =
    useHistoryDetail(selectedId);

  const options = useMemo(() => {
    if (!records?.length) return [];
    return records.map((r) => ({
      value: String(r.id),
      label: `#${r.id} | ${r.created_at} | ${r.jd_position || "未知岗位"} | 匹配度: ${((r.overall_score || 0) * 100).toFixed(0)}%`,
    }));
  }, [records]);

  if (isLoading) {
    return (
      <div className="text-center py-20 text-gray-400">
        <p>加载中...</p>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="text-center py-20 text-red-400">
        <p>读取历史记录失败</p>
        <p className="text-xs mt-1">请确保后端服务已启动</p>
      </div>
    );
  }

  if (!records || records.length === 0) {
    return (
      <div className="text-center py-20 text-gray-400">
        <div className="text-5xl mb-4">📋</div>
        <p className="text-lg font-semibold mb-2">暂无历史记录</p>
        <p className="text-sm">每次分析完成后会自动保存到这里</p>
        <p className="text-sm">请先在「优化」Tab 中完成一次分析</p>
      </div>
    );
  }

  return (
    <div>
      <h2 className="text-lg font-bold text-gray-900 mb-4">📋 历史分析记录</h2>

      <Select
        value={selectedId ? String(selectedId) : ""}
        onValueChange={(v) => setSelectedId(v ? Number(v) : null)}
      >
        <SelectTrigger className="w-full mb-4">
          <SelectValue placeholder="选择历史记录查看详情" />
        </SelectTrigger>
        <SelectContent>
          {options.map((opt) => (
            <SelectItem key={opt.value} value={opt.value}>
              {opt.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      {isLoadingDetail ? (
        <div className="text-center py-12 text-gray-400">
          <p>加载详情中...</p>
        </div>
      ) : detail ? (
        <RecordDetail detail={detail} />
      ) : null}
    </div>
  );
}
