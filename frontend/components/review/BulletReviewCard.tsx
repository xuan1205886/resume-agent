"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";
import { Check, X, Pencil, RotateCcw } from "lucide-react";
import type { BulletScore, FactCheckVerdict, ReviewStatus } from "@/lib/types";

interface BulletReviewCardProps {
  bullet: BulletScore;
  verdict?: FactCheckVerdict;        // 可关联的事实核查
  status: ReviewStatus;
  onAccept: (id: string) => void;
  onReject: (id: string) => void;
  onEdit: (id: string, editedText: string) => void;
  onReset: (id: string) => void;
}

export function BulletReviewCard({
  bullet,
  verdict,
  status,
  onAccept,
  onReject,
  onEdit,
}: BulletReviewCardProps) {
  const [editing, setEditing] = useState(false);
  const [editedText, setEditedText] = useState(
    verdict?.generated_text || bullet.text
  );

  const aiText = verdict?.generated_text || "";
  const driftLevel = verdict?.drift_level || "none";

  const statusBadge = {
    pending: { label: "待审查", className: "bg-gray-100 text-gray-600" },
    accepted: { label: "已接受", className: "bg-green-100 text-green-700" },
    rejected: { label: "已拒绝", className: "bg-red-100 text-red-700" },
    edited: { label: "已编辑", className: "bg-blue-100 text-blue-700" },
  }[status];

  const driftBadge = {
    none: null,
    minor: { label: "轻微漂移", className: "bg-yellow-100 text-yellow-700" },
    major: { label: "严重漂移", className: "bg-red-100 text-red-700" },
    fabricated: { label: "虚构", className: "bg-red-200 text-red-800" },
  }[driftLevel];

  const handleSaveEdit = () => {
    onEdit(bullet.id, editedText);
    setEditing(false);
  };

  return (
    <div
      className={`border rounded-lg p-3 mb-2 transition-colors ${
        status === "accepted"
          ? "border-green-300 bg-green-50/30"
          : status === "rejected"
            ? "border-red-300 bg-red-50/30 opacity-60"
            : "border-gray-200 bg-white"
      }`}
    >
      {/* 头部：来源 + 评分 */}
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2 text-xs">
          <Badge variant="outline" className="text-xs">
            {bullet.source_type === "experience" ? "💼" : "🚀"}{" "}
            {bullet.company || bullet.title}
          </Badge>
          <span className="text-gray-400">|</span>
          <span className="font-mono text-gray-500">
            Score: {bullet.total_score?.toFixed(0) || "—"}
          </span>
          {bullet.matched_skills?.length > 0 && (
            <>
              <span className="text-gray-400">|</span>
              <span className="text-gray-500">
                {bullet.matched_skills.slice(0, 3).join(", ")}
              </span>
            </>
          )}
        </div>
        <div className="flex items-center gap-1">
          {driftBadge && (
            <Badge className={`text-[10px] ${driftBadge.className}`}>
              {driftBadge.label}
            </Badge>
          )}
          <Badge className={`text-[10px] ${statusBadge.className}`}>
            {statusBadge.label}
          </Badge>
        </div>
      </div>

      {/* 原文 */}
      <div className="text-xs text-gray-500 mb-1">
        <span className="font-semibold">原文:</span> {bullet.text}
      </div>

      {/* AI 优化版 */}
      {aiText && aiText !== bullet.text && (
        <div className="text-xs text-blue-700 bg-blue-50 rounded p-2 mb-2">
          <span className="font-semibold">AI 优化:</span>{" "}
          {editing ? (
            <Textarea
              value={editedText}
              onChange={(e) => setEditedText(e.target.value)}
              className="mt-1 text-xs min-h-[60px]"
            />
          ) : (
            aiText
          )}
        </div>
      )}

      {/* 操作按钮 */}
      <div className="flex items-center gap-1 mt-2">
        {editing ? (
          <>
            <Button size="sm" variant="outline" onClick={handleSaveEdit} className="h-7 text-xs">
              <Check className="w-3 h-3 mr-1" /> 保存
            </Button>
            <Button size="sm" variant="ghost" onClick={() => setEditing(false)} className="h-7 text-xs">
              取消
            </Button>
          </>
        ) : (
          <>
            <Button
              size="sm"
              variant={status === "accepted" ? "default" : "outline"}
              onClick={() => onAccept(bullet.id)}
              disabled={status === "accepted"}
              className={`h-7 text-xs ${status === "accepted" ? "bg-green-600 hover:bg-green-700" : ""}`}
            >
              <Check className="w-3 h-3 mr-1" /> 接受
            </Button>
            <Button
              size="sm"
              variant={status === "rejected" ? "default" : "outline"}
              onClick={() => onReject(bullet.id)}
              disabled={status === "rejected"}
              className={`h-7 text-xs ${status === "rejected" ? "bg-red-600 hover:bg-red-700" : ""}`}
            >
              <X className="w-3 h-3 mr-1" /> 拒绝
            </Button>
            <Button
              size="sm"
              variant="ghost"
              onClick={() => {
                setEditedText(aiText || bullet.text);
                setEditing(true);
              }}
              className="h-7 text-xs"
            >
              <Pencil className="w-3 h-3 mr-1" /> 编辑
            </Button>
            {(status === "accepted" || status === "rejected" || status === "edited") && (
              <Button
                size="sm"
                variant="ghost"
                onClick={() => onReset(bullet.id)}
                className="h-7 text-xs text-gray-400"
                title="撤销回待审查状态"
              >
                <RotateCcw className="w-3 h-3 mr-1" /> 撤销
              </Button>
            )}
          </>
        )}
      </div>
    </div>
  );
}
