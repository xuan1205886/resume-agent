"use client";

import { useState, useCallback } from "react";
import { Upload, FileText } from "lucide-react";

interface ResumeUploadProps {
  file: File | null;
  onFileChange: (file: File | null) => void;
  disabled: boolean;
}

export function ResumeUpload({ file, onFileChange, disabled }: ResumeUploadProps) {
  const [isDragOver, setIsDragOver] = useState(false);

  const handleFile = useCallback(
    (selectedFile: File | null) => {
      if (!selectedFile) return;
      if (selectedFile.type !== "application/pdf" && !selectedFile.name.toLowerCase().endsWith(".pdf")) {
        alert("仅支持 PDF 文件");
        return;
      }
      const maxSize = 10 * 1024 * 1024; // 10MB
      if (selectedFile.size > maxSize) {
        alert(`文件过大（${(selectedFile.size / 1024 / 1024).toFixed(1)}MB）。最大允许 10MB。`);
        return;
      }
      onFileChange(selectedFile);
    },
    [onFileChange]
  );

  return (
    <div>
      <label className="text-sm font-semibold text-gray-700 mb-1.5 block">
        📄 上传简历 (PDF)
      </label>
      <div
        className={`border-2 border-dashed rounded-lg p-4 text-center transition-colors ${
          isDragOver
            ? "border-blue-400 bg-blue-50"
            : "border-gray-300 hover:border-gray-400"
        } ${disabled ? "opacity-50 cursor-not-allowed" : "cursor-pointer"}`}
        onDragOver={(e) => {
          e.preventDefault();
          if (!disabled) setIsDragOver(true);
        }}
        onDragLeave={() => setIsDragOver(false)}
        onDrop={(e) => {
          e.preventDefault();
          setIsDragOver(false);
          if (!disabled) {
            handleFile(e.dataTransfer.files[0] || null);
          }
        }}
      >
        {file ? (
          <div className="flex items-center justify-center gap-2 text-sm text-green-600">
            <FileText className="w-4 h-4" />
            <span className="font-medium">{file.name}</span>
            <span className="text-gray-400">
              ({(file.size / 1024).toFixed(1)} KB)
            </span>
            {!disabled && (
              <button
                type="button"
                onClick={() => onFileChange(null)}
                className="text-red-500 hover:text-red-700 ml-2"
              >
                移除
              </button>
            )}
          </div>
        ) : (
          <label className="flex flex-col items-center gap-1 cursor-pointer">
            <Upload className="w-6 h-6 text-gray-400" />
            <span className="text-sm text-gray-500">
              拖拽 PDF 文件到此处，或点击选择
            </span>
            <input
              type="file"
              accept=".pdf,application/pdf"
              className="hidden"
              disabled={disabled}
              onChange={(e) => handleFile(e.target.files?.[0] || null)}
            />
          </label>
        )}
      </div>
    </div>
  );
}
