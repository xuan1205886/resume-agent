"""
API 鉴权与速率限制 — API Key 认证 + 滑动窗口速率限制
"""

import time
import threading
from collections import defaultdict
from typing import Optional

from fastapi import Header, HTTPException, Request

from src.config import get_config


# ===== API Key 鉴权 =====


def verify_api_key(x_api_key: Optional[str] = Header(None)) -> Optional[str]:
    """验证 API Key（如果配置了 api_key 则强制校验，否则跳过）

    用法:
        @app.post("/api/v1/xxx")
        async def endpoint(api_key: str = Depends(verify_api_key)):
            ...

    Raises:
        HTTPException 401: API Key 缺失或不匹配
    """
    config = get_config()
    expected_key = config.server.api_key

    if not expected_key:
        # 未配置 API Key，跳过鉴权（开发环境）
        return None

    if not x_api_key:
        raise HTTPException(
            status_code=401,
            detail="缺少 API Key。请在请求头中添加 X-API-Key。",
        )

    if x_api_key != expected_key:
        raise HTTPException(
            status_code=401,
            detail="API Key 无效。",
        )

    return x_api_key


# ===== 滑动窗口速率限制 =====


class RateLimiter:
    """基于滑动窗口的内存速率限制器（线程安全）"""

    def __init__(self, max_requests: int = 30, window_seconds: int = 60):
        """
        Args:
            max_requests: 时间窗口内最大请求数
            window_seconds: 时间窗口（秒），默认 60 秒
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._clients: dict[str, list[float]] = defaultdict(list)
        self._lock = threading.Lock()

    def is_allowed(self, client_id: str) -> bool:
        """检查客户端是否超过速率限制"""
        if self.max_requests <= 0:
            return True  # 不限制

        now = time.time()
        window_start = now - self.window_seconds

        with self._lock:
            # 清理过期记录
            timestamps = self._clients[client_id]
            self._clients[client_id] = [t for t in timestamps if t > window_start]

            if len(self._clients[client_id]) >= self.max_requests:
                return False

            self._clients[client_id].append(now)
            return True

    def cleanup(self):
        """清理所有过期记录（可定期调用防止内存泄漏）"""
        now = time.time()
        window_start = now - self.window_seconds
        with self._lock:
            for client_id in list(self._clients.keys()):
                self._clients[client_id] = [
                    t for t in self._clients[client_id] if t > window_start
                ]
                if not self._clients[client_id]:
                    del self._clients[client_id]


# 全局单例
_rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter() -> RateLimiter:
    """获取速率限制器单例"""
    global _rate_limiter
    if _rate_limiter is None:
        config = get_config()
        _rate_limiter = RateLimiter(
            max_requests=config.server.rate_limit_per_minute,
            window_seconds=60,
        )
    return _rate_limiter


def check_rate_limit(request: Request) -> None:
    """FastAPI 依赖：检查速率限制

    Raises:
        HTTPException 429: 超过速率限制
    """
    limiter = get_rate_limiter()

    # 获取客户端 IP：优先用直连 IP；若配置了反向代理则用 X-Forwarded-For
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded and (request.client.host in ("127.0.0.1", "::1")):
        # 反向代理场景：取 X-Forwarded-For 的第一个 IP
        client_id = forwarded.split(",")[0].strip()
    else:
        client_id = request.client.host if request.client else "unknown"

    if not limiter.is_allowed(client_id):
        raise HTTPException(
            status_code=429,
            detail=f"请求过于频繁，请稍后再试（每分钟最多 {limiter.max_requests} 次请求）。",
        )
