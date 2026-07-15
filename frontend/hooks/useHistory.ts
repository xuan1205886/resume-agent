/**
 * useHistory — TanStack Query hooks 用于历史记录查询
 */

import { useQuery } from "@tanstack/react-query";
import { getHistory, getHistoryDetail } from "@/lib/api";
import type { HistoryRecord, HistoryDetail } from "@/lib/types";

export function useHistoryList(limit = 50) {
  return useQuery<HistoryRecord[]>({
    queryKey: ["history", limit],
    queryFn: () => getHistory(limit),
    staleTime: 60_000,
  });
}

export function useHistoryDetail(id: number | null) {
  return useQuery<HistoryDetail>({
    queryKey: ["history", id],
    queryFn: () => getHistoryDetail(id!),
    enabled: id !== null,
    staleTime: 60_000,
  });
}
