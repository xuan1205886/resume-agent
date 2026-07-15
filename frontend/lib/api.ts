/**
 * API 客户端 — 封装对 FastAPI 后端的 HTTP 请求
 */

import { API_BASE_URL } from "./constants";

// ===== 通用请求辅助 =====

function getHeaders(): HeadersInit {
  const headers: HeadersInit = {};
  const apiKey = process.env.NEXT_PUBLIC_API_KEY;
  if (apiKey) {
    headers["X-API-Key"] = apiKey;
  }
  return headers;
}

async function fetchAPI<T>(
  path: string,
  options?: RequestInit
): Promise<T> {
  const url = `${API_BASE_URL}${path}`;
  const res = await fetch(url, {
    ...options,
    headers: {
      ...getHeaders(),
      ...options?.headers,
    },
  });
  if (!res.ok) {
    const errorText = await res.text().catch(() => "Unknown error");
    throw new Error(`API ${res.status}: ${errorText}`);
  }
  return res.json();
}

// ===== 健康检查 =====

export async function checkHealth(): Promise<{ status: string; version: string }> {
  return fetchAPI("/api/v1/health");
}

// ===== 历史记录 =====

import type { HistoryRecord, HistoryDetail } from "./types";

export async function getHistory(limit = 50): Promise<HistoryRecord[]> {
  return fetchAPI(`/api/v1/history?limit=${limit}`);
}

export async function getHistoryDetail(id: number): Promise<HistoryDetail> {
  return fetchAPI(`/api/v1/history/${id}`);
}

// ===== 单步调试端点 (unused in normal flow, but available) =====

export async function parseJD(jdText: string) {
  return fetchAPI("/api/v1/parse/jd", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ jd_text: jdText }),
  });
}

export async function parseResume(file: File) {
  const formData = new FormData();
  formData.append("resume_file", file);
  return fetchAPI("/api/v1/parse/resume", {
    method: "POST",
    body: formData,
  });
}
