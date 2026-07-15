/**
 * useOptimizePipeline — SSE 事件处理 + 流水线状态管理
 *
 * 对应 Python app.py 的 run_pipeline_via_api() + handle_sse_event()
 */

import { useCallback, useRef } from "react";
import { usePipelineStore } from "@/stores/pipelineStore";
import { streamOptimize } from "@/lib/sse";
import type { SSEEvent, OptimizationResult } from "@/lib/types";

export function useOptimizePipeline() {
  const store = usePipelineStore();
  const abortRef = useRef<AbortController | null>(null);

  /**
   * 处理单个 SSE 事件（对应 Python handle_sse_event）
   */
  const handleSSEEvent = useCallback(
    (event: SSEEvent) => {
      switch (event.type) {
        case "pipeline_start": {
          const agents = (event.data.agents as Array<{
            step: number;
            name: string;
            title: string;
            icon: string;
          }>) || [];
          store.setAllStepsRunning(agents);
          break;
        }

        case "step_start":
          store.setStepRunning(event.step, event.message);
          break;

        case "step_complete": {
          const data = event.data || {};
          // 跳过的 Agent 也标记为 complete
          store.setStepComplete(event.step, data as Record<string, unknown>);
          break;
        }

        case "step_error":
          store.setStepError(event.step, event.message || "Agent 执行失败");
          break;

        case "done":
          store.setPipelineDone(event.data as unknown as OptimizationResult);
          break;

        case "error":
          store.setErrorMessage(event.message || "未知错误");
          break;

        default:
          console.warn("[SSE] 未知事件类型:", event.type);
      }
    },
    [store]
  );

  /**
   * 开始执行流水线
   */
  const startPipeline = useCallback(
    async (jdText: string, resumeFile: File) => {
      // 取消上一次请求（避免并发泄漏）
      abortRef.current?.abort();
      store.resetPipeline();
      store.setErrorMessage("");

      const controller = new AbortController();
      abortRef.current = controller;

      try {
        await streamOptimize(jdText, resumeFile, handleSSEEvent, controller.signal);
      } catch (err: unknown) {
        if (err instanceof DOMException && err.name === "AbortError") {
          // 用户主动取消
          return;
        }
        const message =
          err instanceof TypeError && err.message.includes("fetch")
            ? `无法连接到 ${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8765"}。请确保后端已启动：python -m uvicorn api_server:app --host 127.0.0.1 --port 8765`
            : err instanceof Error
              ? err.message
              : String(err);
        store.setErrorMessage(message);
      }
    },
    [store, handleSSEEvent]
  );

  /**
   * 取消流水线
   */
  const abort = useCallback(() => {
    abortRef.current?.abort();
    store.setPipelineStopped();
  }, [store]);

  return {
    startPipeline,
    abort,
    pipelineRunning: store.pipelineRunning,
    pipelineDone: store.pipelineDone,
    steps: store.steps,
    result: store.result,
    errorMessage: store.errorMessage,
    factCheck: store.factCheck,
    resetPipeline: store.resetPipeline,
  };
}
