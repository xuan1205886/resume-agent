"""
FastAPI 应用主入口 — 简历优化Agent API 服务
提供 SSE 流式优化的 REST API
"""

import asyncio
import json
import logging
import os
import sys
import tempfile
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from src.api.auth import check_rate_limit, verify_api_key
from src.api.schemas import (
    HealthResponse,
    JDParseRequest,
    MatchRequest,
    OptimizeRequest,
    SuggestRequest,
    WriteRequest,
)
from src.api.session import get_session_manager
from src.config import get_config
from src.agent.graph import AGENT_META, run_pipeline
from src.agent.registry import AgentRegistry
from src.parsing.jd_parser import parse_jd
from src.parsing.resume_parser import extract_text_from_pdf, structure_resume, build_resume_sections

# 配置日志
from src.logging_config import get_log_level_from_env, setup_logging
setup_logging(level=get_log_level_from_env())
logger = logging.getLogger("api_server")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期"""
    cleanup_task = asyncio.create_task(_cleanup_loop())
    logger.info("AI Resume Optimizer API 启动完成")
    yield
    cleanup_task.cancel()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        pass
    logger.info("AI Resume Optimizer API 已关闭")


async def _cleanup_loop():
    """定期清理过期会话和速率限制记录"""
    while True:
        await asyncio.sleep(300)  # 每 5 分钟
        try:
            session_mgr = get_session_manager()
            session_mgr.cleanup_expired()

            from src.api.auth import get_rate_limiter
            get_rate_limiter().cleanup()
        except Exception:
            pass


config = get_config()
app = FastAPI(
    title="AI Resume Optimizer",
    version="2.0.0",
    description="AI驱动的简历优化Agent — 6 Agent Multi-Agent + Tool Calling",
    lifespan=lifespan,
)

# 安全：非本地环境必须配置 API Key
_is_local = config.server.host in ("127.0.0.1", "localhost", "::1")
if not config.server.api_key and not _is_local:
    logger.error("[!] FATAL: API Key not configured for non-localhost deployment.")
    logger.error("[!] Set server.api_key in config.yaml or RESUME_API_KEY env variable.")
    logger.error("[!] Refusing to start with public endpoints unprotected.")
    import sys; sys.exit(1)
elif not config.server.api_key:
    logger.warning("[!] API Key not configured — endpoints are public (localhost only)")
else:
    logger.info("[OK] API Key authentication enabled")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.server.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ===== 健康检查 =====

@app.get("/api/v1/health", response_model=HealthResponse)
async def health():
    return HealthResponse()


# ===== 主端点：SSE 流式优化 =====

@app.post("/api/v1/optimize/stream")
def optimize_stream(
    jd_text: str = Form(...),
    resume_file: UploadFile = File(...),
    api_key: str = Depends(verify_api_key),
    rate_check: None = Depends(check_rate_limit),
):
    """主端点：上传 JD + 简历 PDF，SSE 流式推送 6 步进度"""
    # 校验文件类型
    _validate_pdf_upload(resume_file)

    content = resume_file.file.read()

    # 保存到临时文件
    suffix = os.path.splitext(resume_file.filename or "resume.pdf")[1] or ".pdf"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    async def event_generator():
        tmp_path_local = tmp_path

        # 发送 pipeline_start（从 Registry 动态生成）
        total = AgentRegistry.total_steps()
        agents_meta = AgentRegistry.get_meta_for_sse()
        yield _sse_event("pipeline_start", step=0, node="", message=f"{total}个Agent分阶段并行执行中...", data={
            "total_steps": total,
            "agents": agents_meta,
        })

        final_state = {}
        graph_error = None

        # Step 0: PDF 文本提取
        raw_text = ""
        try:
            raw_text = await _run_with_timeout(extract_text_from_pdf, tmp_path_local, timeout_seconds=30)
        except Exception as e:
            logger.error(f"PDF提取失败: {e}")
            graph_error = str(e)

        # Step 1-4: 运行 Agent Graph（真流式：线程 + 队列）
        completed_agents = set()
        if not graph_error and raw_text:
            try:
                event_queue: asyncio.Queue = asyncio.Queue()

                def _run_graph_in_thread():
                    try:
                        graph_stream = run_pipeline(
                            jd_text=jd_text,
                            resume_text=raw_text,
                            resume_pdf_path=tmp_path_local,
                            stream=True,
                        )
                        for update in graph_stream:
                            asyncio.run_coroutine_threadsafe(
                                event_queue.put(("update", update)),
                                loop,
                            )
                        asyncio.run_coroutine_threadsafe(
                            event_queue.put(("done", None)),
                            loop,
                        )
                    except Exception as exc:
                        asyncio.run_coroutine_threadsafe(
                            event_queue.put(("error", exc)),
                            loop,
                        )

                loop = asyncio.get_running_loop()
                thread_task = asyncio.create_task(asyncio.to_thread(_run_graph_in_thread))

                while True:
                    event_type, event_data = await event_queue.get()
                    if event_type == "done":
                        break
                    elif event_type == "error":
                        raise event_data
                    else:
                        update = event_data
                        for agent_name, agent_output in update.items():
                            completed_agents.add(agent_name)
                            _merge_state(final_state, agent_name, agent_output)
                            if not agent_output.get("_skipped"):
                                yield _make_agent_start_sse(agent_name)
                            yield _make_agent_sse(agent_name, agent_output)

                await thread_task

            except Exception as e:
                logger.error(f"Agent Graph 执行失败: {e}", exc_info=True)
                graph_error = str(e)

        # 确保所有必需的 Agent 都有结果（缺失的用 skipped 补上）
        for agent in AgentRegistry.list_required():
            if agent.name not in completed_agents:
                reason = graph_error or "上游步骤失败"
                skipped_output = {"error": "", "_skipped": True, "_skip_reason": reason}
                _merge_state(final_state, agent.name, skipped_output)
                yield _make_agent_sse(agent.name, skipped_output)

        # 构建最终结果
        done_data = _build_done_data(final_state)

        # 保存历史（失败不影响结果返回）
        try:
            from src.storage.history import save_analysis
            save_analysis(done_data)
            logger.info("历史记录已保存")
        except Exception as save_err:
            logger.error(f"保存历史记录失败: {save_err}")

        # 发送 done
        yield _sse_event("done", step=total, node="", data=done_data)

        # 清理临时文件
        try:
            os.unlink(tmp_path_local)
        except Exception:
            pass

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


async def _run_with_timeout(func, *args, timeout_seconds: int = 120):
"""在线程池中运行同步函数，带超时控制
Args:
func: 同步函数
*args: 函数参数
timeout_seconds: 超时时间（秒）
Returns:
函数执行结果
Raises:
asyncio.TimeoutError: 执行超时
"""
return await asyncio.wait_for(
asyncio.to_thread(func, *args),
timeout=timeout_seconds,
)
def _sse_event(event_type: str, step: int = 0, node: str = "", data: dict = None, message: str = ""):
"""构建 SSE 事件字符串"""
payload = {
"type": event_type,
"step": step,
"node": node,
"data": data or {},
"message": message,
}
return f"event: {event_type}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"
def _sanitize_sse_data(obj, max_depth: int = 5, max_str_len: int = 5000):
"""净化 SSE 数据，防止 LLM 输出中的控制字符或过大内容破坏 SSE 帧
递归处理 dict/list/str，截断过长字符串，移除控制字符。
"""
if max_depth <= 0:
return "[truncated: max depth]"
if isinstance(obj, str):
# 标准化换行符（Windows → Unix），但保留段落分隔符
# 注意: json.dumps 会将 \n 转义为 \\n，不会在 SSE wire format 中产生
# 字面的 \n\n 事件分隔符，因此不需要合并双换行。
sanitized = obj.replace("\r\n", "\n").replace("\r", "\n")
if len(sanitized) > max_str_len:
    sanitized = sanitized[:max_str_len] + "...[truncated]"
return sanitized
elif isinstance(obj, dict):
return {k: _sanitize_sse_data(v, max_depth - 1, max_str_len) for k, v in obj.items()}
elif isinstance(obj, list):
return [_sanitize_sse_data(item, max_depth - 1, max_str_len) for item in obj[:50]]  # 最多50条
else:
return obj
def _merge_state(final_state: dict, agent_name: str, agent_output: dict):
"""将 Agent 输出合并到累积状态中"""
final_state[agent_name] = agent_output
for k, v in agent_output.items():
final_state[k] = v
def _make_agent_sse(agent_name: str, agent_output: dict) -> str:
"""为单个 Agent 构建 SSE step_complete/step_error 事件字符串"""
meta = AGENT_META.get(agent_name, {"step": 0, "title": agent_name, "icon": "🔄"})
step = meta["step"]
title = meta["title"]
icon = meta["icon"]
if agent_output.get("_skipped"):
return _sse_agent_event(
    "step_complete", agent_name, step,
    f"{icon} {title}: ⏭️ 跳过 ({agent_output.get('_skip_reason', '')})",
    agent_output,
)
elif agent_output.get("error"):
return _sse_agent_event(
    "step_error", agent_name, step,
    f"{icon} {title}: {agent_output['error']}",
    agent_output,
)
else:
return _sse_agent_event(
    "step_complete", agent_name, step,
    f"{icon} {title} 完成",
    agent_output,
)
def _make_agent_start_sse(agent_name: str) -> str:
"""为单个 Agent 构建 SSE step_start 事件"""
meta = AGENT_META.get(agent_name, {"step": 0, "title": agent_name, "icon": "🔄"})
return _sse_agent_event(
"step_start", agent_name, meta["step"],
f"{meta['icon']} {meta['title']} 执行中...",
)
def _build_done_data(final_state: dict) -> dict:
"""从 Agent 累积状态中动态构建最终的 done 数据
字段列表由 AgentRegistry 的 output_fields 自动生成，不再硬编码。
"""
data = {}
for field in AgentRegistry.get_all_output_fields():
# 根据字段名推断合理的默认值
if field.endswith("_count") or field.endswith("_score"):
    data[field] = final_state.get(field, 0)
elif field.endswith("_md") or field.endswith("_summary") or field.endswith("_advice"):
    data[field] = final_state.get(field, "")
elif field.endswith("_skills") or field.endswith("_results") or field.endswith("_questions") or field.endswith("_suggestions"):
    data[field] = final_state.get(field, [])
elif field == "fact_check" or field == "parsed_resume" or field.endswith("_sections"):
    data[field] = final_state.get(field, {})
else:
    data[field] = final_state.get(field, "")
return data
def _sse_agent_event(event_type: str, agent_name: str, step: int, message: str, data: dict = None):
"""构建 Agent SSE 事件（与前端步骤卡片兼容）"""
payload = {
"type": event_type,
"step": step,
"node": agent_name,
"data": _sanitize_sse_data(data or {}),
"message": _sanitize_sse_data(message, max_str_len=500),
}
return f"event: {event_type}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"
def _validate_pdf_upload(upload_file: UploadFile) -> None:
"""校验 PDF 上传文件的类型和大小
Raises:
HTTPException 400: 文件类型不是 PDF 或大小超限
"""
# 检查 MIME 类型
content_type = upload_file.content_type or ""
if content_type and content_type != "application/pdf":
raise HTTPException(
    status_code=400,
    detail=f"不支持的文件类型: {content_type}。请上传 PDF 文件。",
)
# 检查文件扩展名
filename = (upload_file.filename or "").lower()
if filename and not filename.endswith(".pdf"):
raise HTTPException(
    status_code=400,
    detail=f"不支持的文件扩展名。请上传 .pdf 文件。",
)
# 检查文件大小（最大 10MB）
upload_file.file.seek(0, 2)
file_size = upload_file.file.tell()
upload_file.file.seek(0)
max_size = 10 * 1024 * 1024  # 10MB
if file_size > max_size:
raise HTTPException(
    status_code=400,
    detail=f"文件过大（{file_size / 1024 / 1024:.1f}MB）。最大允许 10MB。",
)
# ===== 单独步骤端点（调试用） =====
@app.post("/api/v1/parse/jd")
async def parse_jd_endpoint(
req: JDParseRequest,
api_key: str = Depends(verify_api_key),
rate_check: None = Depends(check_rate_limit),
):
"""Step 1: 仅解析 JD"""
result = parse_jd(req.jd_text)
return result
@app.post("/api/v1/parse/resume")
async def parse_resume_endpoint(
resume_file: UploadFile = File(...),
api_key: str = Depends(verify_api_key),
rate_check: None = Depends(check_rate_limit),
):
"""Step 2: 仅解析简历"""
_validate_pdf_upload(resume_file)
suffix = os.path.splitext(resume_file.filename or "resume.pdf")[1] or ".pdf"
with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
content = await resume_file.read()
tmp.write(content)
tmp_path = tmp.name
    try:
raw_text = extract_text_from_pdf(tmp_path)
parsed = structure_resume(raw_text)
sections = build_resume_sections(parsed)
return {"parsed": parsed, "sections": sections, "raw_length": len(raw_text)}
finally:
os.unlink(tmp_path)


@app.post("/api/v1/match")
async def match_endpoint(
req: MatchRequest,
api_key: str = Depends(verify_api_key),
rate_check: None = Depends(check_rate_limit),
):
"""Step 3: 仅技能匹配"""
result = match_skills(req.jd_skills, req.resume_sections)
return result


@app.post("/api/v1/suggest")
async def suggest_endpoint(
req: SuggestRequest,
api_key: str = Depends(verify_api_key),
rate_check: None = Depends(check_rate_limit),
):
"""Step 4: 仅生成建议"""
result = generate_suggestions(
req.jd_summary,
[],  # jd_skills not needed if match_results is provided
req.resume_sections,
req.match_results,
)
return result


@app.post("/api/v1/write")
async def write_endpoint(
req: WriteRequest,
api_key: str = Depends(verify_api_key),
rate_check: None = Depends(check_rate_limit),
):
"""Step 5: 仅生成简历"""
result = write_optimized_resume(
jd_summary=req.jd_summary,
jd_position="Target Position",
resume_sections=req.resume_sections,
parsed_resume={},
match_results=req.match_results,
suggestions=req.suggestions,
)
return {"optimized_resume_md": result}


# ===== 历史记录端点 =====

@app.get("/api/v1/history")
async def list_history(
limit: int = 50,
api_key: str = Depends(verify_api_key),
):
"""获取历史分析记录列表"""
from src.storage.history import get_history
return get_history(limit)


@app.get("/api/v1/history/{record_id}")
async def get_history_detail(
record_id: int,
api_key: str = Depends(verify_api_key),
):
"""获取单条历史分析记录详情"""
from src.storage.history import get_analysis_by_id
detail = get_analysis_by_id(record_id)
if detail is None:
raise HTTPException(status_code=404, detail="记录不存在")
return detail
