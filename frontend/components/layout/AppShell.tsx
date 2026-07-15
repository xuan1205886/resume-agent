"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { checkHealth } from "@/lib/api";
import { NAV_TABS } from "@/lib/constants";
import { Menu, X } from "lucide-react";

const ICONS: Record<string, string> = {
  "/optimize": "M12 4.5C7 4.5 2.73 7.61 1 12c1.73 4.39 6 7.5 11 7.5s9.27-3.11 11-7.5c-1.73-4.39-6-7.5-11-7.5zM12 17c-2.76 0-5-2.24-5-5s2.24-5 5-5 5 2.24 5 5-2.24 5-5 5zm0-8c-1.66 0-3 1.34-3 3s1.34 3 3 3 3-1.34 3-3-1.34-3-3-3z",
  "/evaluation": "M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zM9 17H7v-7h2v7zm4 0h-2V7h2v10zm4 0h-2v-4h2v4z",
  "/ats-parser": "M14 2H6c-1.1 0-1.99.9-1.99 2L4 20c0 1.1.89 2 1.99 2H18c1.1 0 2-.9 2-2V8l-6-6zm2 16H8v-2h8v2zm0-4H8v-2h8v2zm-3-5V3.5L18.5 9H13z",
  "/prompts": "M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25zM20.71 7.04c.39-.39.39-1.02 0-1.41l-2.34-2.34c-.39-.39-1.02-.39-1.41 0l-1.83 1.83 3.75 3.75 1.83-1.83z",
  "/history": "M13 3a9 9 0 0 0-9 9H1l3.89 3.89.07.14L9 12H6c0-3.87 3.13-7 7-7s7 3.13 7 7-3.13 7-7 7c-1.93 0-3.68-.79-4.94-2.06l-1.42 1.42A8.954 8.954 0 0 0 13 21a9 9 0 0 0 0-18zm-1 5v5l4.28 2.54.72-1.21-3.5-2.08V8H12z",
};

function SidebarContent({ pathname }: { pathname: string }) {
  const { data: health, isError } = useQuery({
    queryKey: ["health"],
    queryFn: checkHealth,
    refetchInterval: 30_000,
    retry: false,
  });

  return (
    <>
      {/* Logo */}
      <Link href="/optimize" className="px-5 pt-6 pb-5 block">
        <div className="flex items-center gap-2.5">
          <span className="flex items-center justify-center w-8 h-8 rounded-lg bg-blue-600 text-white font-bold text-sm">
            AI
          </span>
          <div className="leading-tight">
            <div className="text-sm font-semibold text-gray-900">简历优化</div>
            <div className="text-[10px] text-gray-400">Resume Agent</div>
          </div>
        </div>
      </Link>

      {/* 导航菜单 */}
      <nav className="flex-1 px-3 py-2 space-y-0.5">
        {NAV_TABS.map((tab) => {
          const isActive = pathname === tab.href ||
            (tab.href !== "/optimize" && pathname.startsWith(tab.href));
          return (
            <Link
              key={tab.href}
              href={tab.href}
              className={`flex items-center gap-3 px-3 py-2 rounded-md text-[13px] font-medium transition-colors ${
                isActive
                  ? "bg-blue-50 text-blue-700"
                  : "text-gray-600 hover:bg-gray-50 hover:text-gray-900"
              }`}
            >
              <svg className="w-4 h-4 shrink-0" viewBox="0 0 24 24" fill="currentColor">
                <path d={ICONS[tab.href] || "M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"} />
              </svg>
              {tab.label}
            </Link>
          );
        })}
      </nav>

      {/* 底部状态 */}
      <div className="px-5 py-4 border-t border-gray-100">
        <div className="flex items-center gap-2 text-[11px] text-gray-400">
          <span className={`inline-block w-1.5 h-1.5 rounded-full ${
            isError ? "bg-red-400" : health ? "bg-green-400" : "bg-yellow-400"
          }`} />
          {isError ? "API 离线" : health ? `API v${health.version}` : "检测中..."}
        </div>
      </div>
    </>
  );
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <div className="flex min-h-full bg-gray-50">
      {/* 桌面端：固定侧边栏 */}
      <aside className="hidden md:flex w-56 shrink-0 bg-white border-r border-gray-200 flex-col">
        <SidebarContent pathname={pathname} />
      </aside>

      {/* 移动端：滑出侧边栏 */}
      {mobileOpen && (
        <div className="md:hidden fixed inset-0 z-50 flex">
          <div className="absolute inset-0 bg-black/30" onClick={() => setMobileOpen(false)} />
          <aside className="relative w-56 bg-white border-r border-gray-200 flex flex-col animate-slide-in">
            <button
              className="absolute top-3 right-3 p-1 text-gray-400 hover:text-gray-600"
              onClick={() => setMobileOpen(false)}
            >
              <X className="w-5 h-5" />
            </button>
            <SidebarContent pathname={pathname} />
          </aside>
        </div>
      )}

      {/* 移动端：顶部小导航栏 */}
      <div className="md:hidden fixed top-0 left-0 right-0 z-40 bg-white border-b border-gray-200 flex items-center justify-between px-4 h-12">
        <button onClick={() => setMobileOpen(true)} className="p-1 text-gray-500">
          <Menu className="w-5 h-5" />
        </button>
        <Link href="/optimize" className="text-sm font-semibold text-gray-900">
          AI 简历优化
        </Link>
        <div className="w-5" /> {/* 占位保持居中 */}
      </div>

      {/* 移动端：底部 Tab 栏 */}
      <nav className="md:hidden fixed bottom-0 left-0 right-0 z-40 bg-white border-t border-gray-200 flex justify-around py-1.5">
        {NAV_TABS.map((tab) => {
          const isActive = pathname === tab.href ||
            (tab.href !== "/optimize" && pathname.startsWith(tab.href));
          return (
            <Link
              key={tab.href}
              href={tab.href}
              className={`flex flex-col items-center gap-0.5 px-2 py-1 text-[10px] transition-colors ${
                isActive ? "text-blue-600" : "text-gray-400"
              }`}
            >
              <svg className="w-4 h-4" viewBox="0 0 24 24" fill="currentColor">
                <path d={ICONS[tab.href] || ""} />
              </svg>
              {tab.label}
            </Link>
          );
        })}
      </nav>

      {/* 主内容区 */}
      <div className="flex-1 flex flex-col min-w-0">
        <main className="flex-1 max-w-5xl mx-auto w-full px-4 md:px-8 pt-12 md:pt-6 pb-14 md:pb-6">
          {children}
        </main>
        <footer className="hidden md:block text-center py-4 text-[11px] text-gray-400">
          Powered by LangGraph + DeepSeek
        </footer>
      </div>
    </div>
  );
}
