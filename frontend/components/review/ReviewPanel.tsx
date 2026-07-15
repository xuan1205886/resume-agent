"use client";

import { useState, useCallback, useMemo } from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { BulletReviewCard } from "./BulletReviewCard";
import type { OptimizationResult, ReviewStatus } from "@/lib/types";

interface ReviewPanelProps {
  result: OptimizationResult;
  onReviewComplete: (acceptedIds: Set<string>, editedTexts: Map<string, string>) => void;
}

export function ReviewPanel({ result, onReviewComplete }: ReviewPanelProps) {
  // 审查状态管理
  const [reviewStates, setReviewStates] = useState<Map<string, ReviewStatus>>(new Map());
  const [editedTexts, setEditedTexts] = useState<Map<string, string>>(new Map());

  const bullets = (result as unknown as Record<string, unknown>).scored_bullets as
    | Array<Record<string, unknown>>
    | undefined;
  const verdicts = result.fact_check?.verdicts || [];

  // 建立 verdict bullet_id 索引
  const verdictByBulletId = useMemo(() => {
    const map = new Map<string, (typeof verdicts)[number]>();
    for (const v of verdicts) {
      const bid = (v as unknown as Record<string, unknown>).bullet_id as string;
      if (bid) map.set(bid, v);
    }
    return map;
  }, [verdicts]);

  const handleAccept = useCallback((id: string) => {
    setReviewStates((prev) => {
      const next = new Map(prev);
      const current = next.get(id);
      // 如果已接受，重置为 pending
      if (current === "accepted") {
        next.set(id, "pending");
      } else {
        next.set(id, "accepted");
      }
      return next;
    });
  }, []);

  const handleReject = useCallback((id: string) => {
    setReviewStates((prev) => {
      const next = new Map(prev);
      const current = next.get(id);
      if (current === "rejected") {
        next.set(id, "pending");
      } else {
        next.set(id, "rejected");
      }
      return next;
    });
  }, []);

  const handleReset = useCallback((id: string) => {
    setReviewStates((prev) => {
      const next = new Map(prev);
      next.set(id, "pending");
      return next;
    });
  }, []);

  const handleEdit = useCallback((id: string, text: string) => {
    setEditedTexts((prev) => {
      const next = new Map(prev);
      next.set(id, text);
      return next;
    });
    setReviewStates((prev) => {
      const next = new Map(prev);
      next.set(id, "edited");
      return next;
    });
    // 通知父组件
    const accepted = new Set<string>();
    const allEdited = new Map(editedTexts);
    allEdited.set(id, text);
    for (const [bid, status] of reviewStates.entries()) {
      if (status === "accepted" || status === "edited") accepted.add(bid);
    }
    accepted.add(id);
    onReviewComplete(accepted, allEdited);
  }, [reviewStates, editedTexts, onReviewComplete]);

  const stats = useMemo(() => {
    let pending = 0, accepted = 0, rejected = 0, edited = 0;
    for (const [, status] of reviewStates) {
      if (status === "pending") pending++;
      else if (status === "accepted") accepted++;
      else if (status === "rejected") rejected++;
      else if (status === "edited") edited++;
    }
    return { pending, accepted, rejected, edited };
  }, [reviewStates]);

  return (
    <div className="mt-6">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-lg font-bold text-gray-900">🔍 逐条审查</h2>
        <div className="flex items-center gap-3 text-xs text-gray-500">
          <span>⏳ {stats.pending} 待审</span>
          <span className="text-green-600">✅ {stats.accepted} 接受</span>
          <span className="text-red-600">❌ {stats.rejected} 拒绝</span>
          <span className="text-blue-600">✏️ {stats.edited} 编辑</span>
        </div>
      </div>

      <Tabs defaultValue="bullets">
        <TabsList className="mb-3">
          <TabsTrigger value="bullets" className="text-xs">
            📋 Bullets ({bullets?.length || 0})
          </TabsTrigger>
          <TabsTrigger value="suggestions" className="text-xs">
            💡 建议 ({result.suggestions?.length || 0})
          </TabsTrigger>
          <TabsTrigger value="factcheck" className="text-xs">
            🛡️ 核查 ({verdicts.length})
          </TabsTrigger>
        </TabsList>

        <TabsContent value="bullets" className="space-y-2 max-h-[600px] overflow-y-auto">
          {!bullets || bullets.length === 0 ? (
            <p className="text-sm text-gray-400 text-center py-8">
              暂无 bullet 数据可审查
            </p>
          ) : (
            bullets.map((b) => {
              const id = b.id as string;
              const status = reviewStates.get(id) || "pending";
              return (
                <BulletReviewCard
                  key={id}
                  bullet={{
                    id,
                    text: (b.text as string) || "",
                    source_type: (b.source_type as string) || "",
                    company: (b.company as string) || "",
                    title: (b.title as string) || "",
                    total_score: (b.total_score as number) || 0,
                    matched_skills: (b.matched_skills as string[]) || [],
                  }}
                  verdict={verdictByBulletId.get(id)}
                  status={status}
                  onAccept={handleAccept}
                  onReject={handleReject}
                  onEdit={handleEdit}
                  onReset={handleReset}
                />
              );
            })
          )}
        </TabsContent>

        <TabsContent value="suggestions" className="max-h-[600px] overflow-y-auto">
          {(!result.suggestions || result.suggestions.length === 0) ? (
            <p className="text-sm text-gray-400 text-center py-8">暂无建议</p>
          ) : (
            result.suggestions.map((s, i) => (
              <div key={i} className="border rounded-lg p-3 mb-2 bg-white">
                <p className="text-xs text-gray-500">
                  <span className="font-semibold">原文:</span> {s.original}
                </p>
                <p className="text-xs text-blue-700 mt-1">
                  <span className="font-semibold">建议:</span> {s.suggestion}
                </p>
                <p className="text-xs text-gray-400 mt-1">{s.reason}</p>
              </div>
            ))
          )}
        </TabsContent>

        <TabsContent value="factcheck" className="max-h-[600px] overflow-y-auto">
          {verdicts.length === 0 ? (
            <p className="text-sm text-gray-400 text-center py-8">暂无核查数据</p>
          ) : (
            verdicts.map((v, i) => (
              <div key={i} className="border rounded-lg p-3 mb-2 bg-white">
                <p className="text-xs text-gray-500">
                  <span className="font-semibold">原文:</span> {v.original_text}
                </p>
                <p className="text-xs text-blue-700 mt-1">
                  <span className="font-semibold">生成:</span> {v.generated_text}
                </p>
                <p className="text-xs text-gray-400 mt-1">{v.explanation}</p>
              </div>
            ))
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}
