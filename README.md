# AI 简历优化 Agent

> AI 驱动的简历优化工具 — 上传 JD 和简历 PDF，4 个 AI Agent 自动分析匹配、生成优化建议、输出 ATS 友好版简历

[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-green.svg)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Next.js-16-black.svg)](https://nextjs.org/)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.2+-purple.svg)](https://langchain-ai.github.io/langgraph/)
[![DeepSeek](https://img.shields.io/badge/LLM-DeepSeek%20%7C%20OpenAI%20%7C%20Claude%20%7C%20Ollama-orange.svg)](#多供应商支持)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## 核心流水线

```
上传 JD + PDF ─→ Agent 1 解析岗位 ─→ Agent 2 解析简历 ─→ Agent 3 技能匹配 ─→ Agent 4 生成优化简历
                  (并行执行)                                   (RAG + LLM)
```

## 技术架构

```
┌─────────────────────────────────────────────────────┐
│                  Next.js 前端 (TypeScript)            │
│         侧边栏导航 + 审查面板 + ATS 解析器             │
└──────────────────────┬──────────────────────────────┘
                       │ SSE 流式
┌──────────────────────┴──────────────────────────────┐
│                    FastAPI 后端                       │
│         /api/v1/optimize/stream (SSE)                │
└──────────────────────┬──────────────────────────────┘
                       │
┌──────────────────────┴──────────────────────────────┐
│                  LangGraph Agent                      │
│  parse_jd → parse_resume → match_skills → optimize   │
│            (两阶段并行 DAG)                           │
└──────────────────────┬──────────────────────────────┘
                       │
┌──────────────────────┴──────────────────────────────┐
│                    知识库 (Chroma)                    │
│  技能分类 + 简历最佳实践 + ATS关键词                   │
│  BGE Embedding + BGE Reranker                        │
└─────────────────────────────────────────────────────┘
```

## 多供应商支持

通过 `config.yaml` 一行切换 LLM 供应商：

| 供应商 | 配置值 | 特点 |
|--------|--------|------|
| DeepSeek | `deepseek` | 默认，高性价比 |
| OpenAI | `openai` | GPT-4o 等 |
| Anthropic | `anthropic` | Claude 系列 |
| Ollama | `ollama` | 本地运行，数据不出机器 |

## 快速开始

### 1. 环境准备

```bash
cd resume-optimizer

# Python 虚拟环境
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # macOS/Linux

# 安装 Python 依赖
pip install -r requirements.txt

# 配置 API Key
cp .env.example .env
# 编辑 .env 填入 DEEPSEEK_API_KEY=sk-xxx
```

### 2. 构建知识库

```bash
python scripts/build_kb.py
```

### 3. 安装前端依赖

```bash
cd frontend
npm install
```

### 4. 启动服务

```bash
# 终端1: 启动 API
python -m uvicorn api_server:app --host 127.0.0.1 --port 8765

# 终端2: 启动前端
cd frontend && npm run dev
```

打开 http://localhost:3000 使用。

### 5. Docker 部署

```bash
docker-compose up -d
# API: http://localhost:8765
# 前端需单独运行: cd frontend && npm run dev
```

## 项目结构

```
resume-optimizer/
├── api_server.py           # FastAPI 后端 + SSE 流式
├── config.yaml             # 全局配置
├── Dockerfile / docker-compose.yml
│
├── src/
│   ├── agent/              # LangGraph Agent（registry + graph + nodes + state + tools）
│   ├── parsing/            # JD解析 + 简历PDF解析
│   ├── matching/           # 技能匹配 (RAG + LLM)
│   ├── optimization/       # 建议生成 + 简历重写 + 事实核查
│   ├── retrieval/          # 向量检索 + BGE Reranker
│   ├── indexing/           # Chroma 索引构建
│   ├── generation/         # 多供应商 LLM 封装
│   ├── api/                # Pydantic Schemas + 会话管理
│   └── config.py           # Pydantic 配置层次
│
├── frontend/               # Next.js 前端
│   ├── app/                # 页面路由（优化/评估/ATS解析/Prompts/历史）
│   ├── components/         # UI 组件（optimize/evaluation/review/ats-parser/...）
│   ├── lib/                # SSE 解析器、ATS 解析库、类型定义
│   ├── hooks/              # 自定义 Hooks（流水线/评估/历史）
│   └── stores/             # Zustand 状态管理
│
├── scripts/
│   ├── build_kb.py         # 知识库构建
│   └── evaluate.py         # 评测脚本
│
├── data/
│   ├── kb/                 # 知识库种子数据
│   └── uploads/            # PDF 上传临时目录
│
└── tests/                  # 单元测试 + 集成测试
```

## 前端功能

| 页面 | 路由 | 功能 |
|------|------|------|
| 优化 | `/optimize` | 上传 JD + PDF，4 Agent 流水线，逐条审查 AI 修改，下载优化版简历 |
| 评估 | `/evaluation` | JD 覆盖率、匹配质量、事实可信度、格式完整度四维指标 |
| ATS 解析 | `/ats-parser` | 浏览器端 PDF 解析，模拟 ATS 系统读取效果，纯规则驱动 |
| Prompts | `/prompts` | 6 个 Agent System Prompt 展示，支持分类筛选和复制 |
| 历史 | `/history` | SQLite 持久化历史记录查询和详情查看 |

## API 端点

| 方法 | 路径 | 用途 |
|------|------|------|
| GET | `/api/v1/health` | 健康检查 |
| POST | `/api/v1/optimize/stream` | **主端点**：SSE 流式优化 |
| POST | `/api/v1/parse/jd` | 解析 JD |
| POST | `/api/v1/parse/resume` | 解析简历 PDF |
| POST | `/api/v1/match` | 技能匹配 |
| POST | `/api/v1/suggest` | 生成建议 |
| POST | `/api/v1/write` | 生成简历 |
| GET | `/api/v1/history` | 历史记录列表 |
| GET | `/api/v1/history/{id}` | 历史记录详情 |

## 评测

```bash
python scripts/evaluate.py          # 快速评测
python scripts/evaluate.py --full   # 完整评测
```

## 技术栈

| 层 | 技术 | 说明 |
|---|------|------|
| 前端 | Next.js 16 + TypeScript + Tailwind CSS | 侧边栏布局 + SSE 实时进度 |
| 后端 | FastAPI | REST API + Server-Sent Events |
| Agent | LangGraph | StateGraph 两阶段并行 DAG |
| LLM | DeepSeek / OpenAI / Anthropic / Ollama | 多供应商统一接口 |
| 向量库 | Chroma | PersistentClient + 余弦空间 |
| Embedding | BGE (Sentence Transformers) | 多语言模型 |
| Reranker | BGE Reranker | Cross-Encoder 精排 |
| PDF解析 | PyMuPDF (后端) + PDF.js (前端) | 服务端 + 浏览器端双解析 |
| 部署 | Docker | 多阶段构建 |

## License

MIT
