/**
 * SSE 流解析器 — fetch ReadableStream 实现（兼容 POST 方式 SSE）
 *
 * 后端使用 POST /api/v1/optimize/stream，标准 EventSource 不支持 POST，
 * 因此需要手动实现 SSE 协议解析。
 */

import type { SSEEvent } from "./types";
import { API_BASE_URL } from "./constants";

export type SSECallback = (event: SSEEvent) => void;

/**
 * 发起 SSE 连接并逐事件回调
 *
 * @param jdText     - 职位描述文本
 * @param resumeFile - 简历 PDF 文件
 * @param onEvent    - 每收到一个 SSE 事件时调用
 * @param signal     - AbortSignal 用于取消
 */
export async function streamOptimize(
  jdText: string,
  resumeFile: File,
  onEvent: SSECallback,
  signal?: AbortSignal
): Promise<void> {
  const formData = new FormData();
  formData.append("jd_text", jdText);
  formData.append("resume_file", resumeFile);

  const headers: HeadersInit = {};
  const apiKey = process.env.NEXT_PUBLIC_API_KEY;
  if (apiKey) {
    headers["X-API-Key"] = apiKey;
  }

  const response = await fetch(`${API_BASE_URL}/api/v1/optimize/stream`, {
    method: "POST",
    body: formData,
    headers,
    signal,
  });

  if (!response.ok) {
    const errorText = await response.text().catch(() => "Unknown error");
    throw new Error(`API error ${response.status}: ${errorText}`);
  }

  const reader = response.body?.getReader();
  if (!reader) {
    throw new Error("Response body is not readable");
  }

  const decoder = new TextDecoder();
  let buffer = "";
  let currentEventType = "";

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      // 保留最后一个不完整的行
      buffer = lines.pop() || "";

      for (const line of lines) {
        const trimmedLine = line.trimEnd();

        if (trimmedLine.startsWith("event: ")) {
          currentEventType = trimmedLine.slice(7).trim();
        } else if (trimmedLine.startsWith("data: ")) {
          const dataStr = trimmedLine.slice(6);
          if (!dataStr) continue;

          try {
            const eventData = JSON.parse(dataStr) as SSEEvent;
            // 如果 event 行未指定类型，使用 data 内的 type 字段
            if (!currentEventType) {
              currentEventType = eventData.type || "";
            }
            onEvent(eventData);
          } catch {
            // 跳过无法解析的 JSON（容错）
            console.warn("[SSE] 跳过不可解析的事件数据");
          }
          // 每个 data 后重置 event type
          currentEventType = "";
        }
        // 空行 = 事件边界，已在 split 时处理
      }
    }
  } finally {
    reader.cancel().catch(() => {});
  }
}
