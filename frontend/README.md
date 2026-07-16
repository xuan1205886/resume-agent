# AI Resume Optimizer — 前端

> Next.js 16 + TypeScript + Tailwind CSS 4 + shadcn/ui

## 页面路由

| 路由 | 页面 | 功能 |
|------|------|------|
| `/` | 首页 | → 重定向到 `/optimize` |
| `/optimize` | 优化主页 | JD 输入 + PDF 上传 → SSE 实时进度 → 优化简历 + 审查模式 |
| `/evaluation` | 评估页 | 4 维评估指标卡片 + 智能 Badcase 诊断面板 |
| `/ats-parser` | ATS 解析 | 纯浏览器端 PDF 解析，不上传服务器，7 维评分 |
| `/prompts` | Prompt 管理 | 6 个 Agent System Prompt 展示，分类筛选 + 复制 |
| `/history` | 历史记录 | SQLite 持久化，下拉选择查看详情 |

## 技术栈

| 类别 | 技术 | 用途 |
|------|------|------|
| 框架 | Next.js 16 (App Router) | 文件即路由 + Server Components |
| UI | React 19 + TypeScript 5 | 类型安全的组件化开发 |
| 样式 | Tailwind CSS 4 + shadcn/ui | 原子化 CSS + 可定制组件库 |
| 状态管理 | Zustand 5 | SSE 流水线状态（步骤/数据/错误） |
| 服务端缓存 | TanStack Query 5 | 健康检查轮询 + 历史记录查询 |
| SSE 解析 | 自研 fetch ReadableStream | POST 请求 SSE（EventSource 只支持 GET） |
| ATS 解析 | PDF.js 6.1 | 浏览器端 4 步算法（参照 OpenResume） |
| Markdown | react-markdown + rehype-sanitize | 简历渲染 + XSS 防护 |

## 组件架构

```
components/
├── layout/
│   ├── AppShell.tsx      # 桌面侧边栏（56px） + 移动端底部 Tab 栏 + 后端健康状态检测
│   └── Providers.tsx     # QueryClientProvider + TanStack Query Devtools
│
├── optimize/             # 优化流程（核心页面）
│   ├── JDInput.tsx       #   职位描述文本输入
│   ├── ResumeUpload.tsx  #   PDF 拖拽上传 + 文件校验
│   ├── ActionButtons.tsx #   开始优化 / 重置 + 取消（AbortController）
│   ├── StepProgress.tsx  #   4 步动态进度条（支持 start/loading/complete/error/skipped）
│   ├── MatchStats.tsx    #   技能匹配统计卡片（匹配率环形图 / 缺失技能列表）
│   ├── SuggestionList.tsx #  优化建议列表（按严重度分级 + 折叠展开）
│   ├── OptimizedResume.tsx # 优化版简历 Markdown 渲染 + 复制 + 下载
│   └── FactCheckPanel.tsx  # 事实核查面板（none/minor/major/fabricated 四级）
│
├── review/               # 审查模式
│   ├── ReviewPanel.tsx   #   审查模式切换 + 全局接受/拒绝
│   └── BulletReviewCard.tsx # 逐条原文 vs AI 改写对比 + 评分 + 编辑
│
├── evaluation/           # 评估页面
│   ├── MetricsGrid.tsx   #   4 列指标卡片网格
│   ├── MetricCard.tsx    #   单指标卡片（百分比 + 颜色分级 + 描述）
│   └── DiagnosisPanel.tsx #  智能诊断面板（critical/warning/info 三级分组）
│
├── ats-parser/           # ATS 解析页面
│   ├── AtsScoreCard.tsx  #   7 维评分雷达图
│   ├── IssueList.tsx     #   检测到的问题列表
│   └── ParsedResult.tsx  #   结构化解析结果展示
│
├── prompts/              # Prompt 管理页面
│   └── PromptCard.tsx    #   单 Prompt 卡片（角色/系统消息/版本/复制）
│
├── history/              # 历史记录页面
│   └── RecordDetail.tsx  #   历史记录详情（优化结果回放）
│
└── ui/                   # shadcn/ui 基础组件
    ├── accordion.tsx     #   折叠面板（DiagnosisPanel 使用）
    ├── badge.tsx         #   状态标签（步骤状态/严重度等）
    ├── button.tsx        #   按钮变体（primary/secondary/ghost/outline）
    ├── card.tsx          #   卡片容器
    ├── progress.tsx      #   进度条
    ├── select.tsx        #   下拉选择
    ├── separator.tsx     #   分割线
    ├── tabs.tsx          #   Tab 切换
    └── textarea.tsx      #   多行文本输入
```

## SSE 流式处理

使用 `fetch` + `ReadableStream` 手动解析 POST SSE 协议（浏览器原生 `EventSource` 仅支持 GET）：

```
POST /api/v1/optimize/stream
  ↓
fetch response.body.getReader()
  ↓
逐 chunk 读取 → 按 \n\n 分割事件帧 → 按 event: / data: 格式解析
  ↓
dispatch 到 Zustand Store → 更新步骤卡片 / 中间数据 / 错误状态
```

## ATS 解析器（纯浏览器端）

4 步算法，完成在浏览器内，**不上传文件到服务器**：

1. **PDF.js 文本提取** — 获取文本项 + 坐标 + 字体 + 字号 + 加粗信息
2. **行分组** (`group-text-items-into-lines`) — Y 坐标分组 + X 坐标排序 + 水平合并
3. **章节检测** (`group-lines-into-sections`) — 200+ 关键词库，中英文双支持
4. **特征评分** (`extract-attributes`) — 7 维打分（姓名/邮箱/电话/章节/教育/经历/技能，满分 100）

## 启动

```bash
npm install
npm run dev        # http://localhost:3000
```

> 确保后端 API 已在 `http://localhost:8765` 启动（配置在 `.env.local` 中的 `NEXT_PUBLIC_API_URL`）。
