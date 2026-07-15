"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeSanitize from "rehype-sanitize";
import type { HistoryDetail } from "@/lib/types";

interface RecordDetailProps {
  detail: HistoryDetail;
}

export function RecordDetail({ detail }: RecordDetailProps) {
  const safeScore = (score: unknown): string => {
    const n = Number(score || 0);
    return isNaN(n) ? "N/A" : `${(n * 100).toFixed(0)}%`;
  };

  return (
    <div>
      {/* 三列指标 */}
      <div className="grid grid-cols-3 gap-3 mb-6">
        <div className="text-center p-4 rounded-lg border bg-white">
          <div className="text-2xl font-bold text-blue-600">
            {safeScore(detail.overall_score)}
          </div>
          <div className="text-sm text-gray-500 mt-1">综合匹配度</div>
        </div>
        <div className="text-center p-4 rounded-lg border bg-white">
          <div className="text-xl font-semibold text-gray-800">
            {detail.jd_position || "未知"}
          </div>
          <div className="text-sm text-gray-500 mt-1">岗位</div>
        </div>
        <div className="text-center p-4 rounded-lg border bg-white">
          <div className="text-lg text-gray-700">
            {detail.created_at || ""}
          </div>
          <div className="text-sm text-gray-500 mt-1">分析时间</div>
        </div>
      </div>

      {/* 优化版简历 */}
      {detail.optimized_resume_md && (
        <div>
          <h3 className="text-base font-bold text-gray-900 mb-3">
            📝 优化版简历
          </h3>
          <div className="border rounded-lg bg-white p-6 prose prose-sm max-w-none prose-headings:text-gray-800 prose-p:text-gray-700">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {detail.optimized_resume_md}
            </ReactMarkdown>
          </div>
        </div>
      )}
    </div>
  );
}
