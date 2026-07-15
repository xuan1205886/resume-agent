"use client";

import { useState, useCallback } from "react";
import dynamic from "next/dynamic";
import { Upload, FileText, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { AtsScoreCard } from "@/components/ats-parser/AtsScoreCard";
import { IssueList } from "@/components/ats-parser/IssueList";
import { ParsedResult } from "@/components/ats-parser/ParsedResult";
import type { ParseResult } from "@/lib/ats-parser";

export default function AtsParserPage() {
  const [file, setFile] = useState<File | null>(null);
  const [parsing, setParsing] = useState(false);
  const [result, setResult] = useState<ParseResult | null>(null);
  const [error, setError] = useState("");
  const [isDragOver, setIsDragOver] = useState(false);

  const handleFile = useCallback(async (f: File | null) => {
    if (!f) return;
    setFile(f);
    setError("");
    setParsing(true);
    setResult(null);

    try {
      // 动态导入 pdfjs-dist，确保仅在浏览器端加载
      const { parseResumeFromPdf } = await import("@/lib/ats-parser");
      const parseResult = await parseResumeFromPdf(f);
      setResult(parseResult);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "PDF 解析失败。请确保文件是有效的文本层 PDF（非扫描件）。"
      );
    } finally {
      setParsing(false);
    }
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragOver(false);
      handleFile(e.dataTransfer.files[0] || null);
    },
    [handleFile]
  );

  return (
    <div className="max-w-6xl mx-auto">
      <div className="mb-6">
        <h2 className="text-lg font-bold text-gray-900">📄 ATS 简历解析器</h2>
        <p className="text-xs text-gray-500 mt-1">
          模拟 ATS 系统（Greenhouse、Lever）读取你的 PDF 简历。
          纯浏览器端运行，数据不上传服务器。
        </p>
      </div>

      {/* 上传区 */}
      {!result && (
        <div
          className={`border-2 border-dashed rounded-xl p-8 text-center transition-colors ${
            isDragOver
              ? "border-blue-400 bg-blue-50"
              : "border-gray-300 hover:border-gray-400"
          }`}
          onDragOver={(e) => {
            e.preventDefault();
            setIsDragOver(true);
          }}
          onDragLeave={() => setIsDragOver(false)}
          onDrop={handleDrop}
        >
          {parsing ? (
            <div className="flex flex-col items-center gap-3">
              <Loader2 className="w-8 h-8 text-blue-500 animate-spin" />
              <p className="text-sm text-gray-500">正在解析简历...</p>
            </div>
          ) : file ? (
            <div className="flex flex-col items-center gap-3">
              <FileText className="w-8 h-8 text-green-500" />
              <p className="text-sm font-medium text-green-600">{file.name}</p>
              <p className="text-xs text-gray-400">
                ({(file.size / 1024).toFixed(1)} KB)
              </p>
              {error && (
                <p className="text-sm text-red-500 mt-2">{error}</p>
              )}
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  setFile(null);
                  setError("");
                }}
              >
                重新选择
              </Button>
            </div>
          ) : (
            <label className="flex flex-col items-center gap-2 cursor-pointer">
              <Upload className="w-10 h-10 text-gray-300" />
              <p className="text-sm text-gray-500">
                <span className="text-blue-500 font-medium">上传 PDF 简历</span>
                {" "}或拖拽到此处
              </p>
              <p className="text-xs text-gray-400">仅支持含文本层的 PDF（非扫描件）</p>
              <input
                type="file"
                accept=".pdf,application/pdf"
                className="hidden"
                onChange={(e) => handleFile(e.target.files?.[0] || null)}
              />
            </label>
          )}
        </div>
      )}

      {/* 错误 */}
      {error && !parsing && !result && (
        <div className="mt-4 bg-red-50 border border-red-200 rounded-lg p-4 text-sm text-red-700">
          <p className="font-semibold">❌ 解析失败</p>
          <p className="mt-1">{error}</p>
        </div>
      )}

      {/* 结果 */}
      {result && (
        <div>
          {/* 重新上传 */}
          <div className="mb-4">
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                setFile(null);
                setResult(null);
                setError("");
              }}
            >
              ← 重新上传
            </Button>
          </div>

          {/* 双栏布局 */}
          <div className="flex gap-6">
            {/* 左栏：评分 + 问题 + 结构化数据 */}
            <div className="w-1/2 space-y-4">
              <AtsScoreCard score={result.score} />
              <IssueList issues={result.score.issues} />
              <ParsedResult resume={result.resume} />
            </div>

            {/* 右栏：PDF 预览 */}
            <div className="w-1/2">
              <div className="border rounded-lg bg-white p-4 sticky top-4">
                <h3 className="font-bold text-gray-900 mb-3">📄 原始 PDF</h3>
                <iframe
                  src={URL.createObjectURL(file!)}
                  className="w-full rounded border"
                  style={{ height: "calc(100vh - 250px)" }}
                  title="PDF Preview"
                />
              </div>
            </div>
          </div>

        </div>
      )}
    </div>
  );
}
