"""
会话管理器 — 复用 rag-qa-system 的内存 TTL 会话模式
"""

import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class Session:
    """会话数据"""
    session_id: str
    created_at: float = field(default_factory=time.time)
    last_active: float = field(default_factory=time.time)
    data: dict = field(default_factory=dict)


class SessionManager:
    """线程安全的内存会话管理器"""

    def __init__(self, ttl_seconds: int = 3600, max_sessions: int = 100):
        self.ttl_seconds = ttl_seconds
        self.max_sessions = max_sessions
        self._sessions: Dict[str, Session] = {}
        self._lock = threading.Lock()

    def create(self, data: Optional[dict] = None) -> Session:
        """创建新会话"""
        with self._lock:
            # 清理过期会话
            self.cleanup_expired()

            # 限制会话数
            if len(self._sessions) >= self.max_sessions:
                # 删除最旧的会话
                oldest = min(self._sessions.values(), key=lambda s: s.last_active)
                del self._sessions[oldest.session_id]

            session_id = uuid.uuid4().hex[:12]
            session = Session(
                session_id=session_id,
                data=data or {},
            )
            self._sessions[session_id] = session
            return session

    def get(self, session_id: str) -> Optional[Session]:
        """获取会话"""
        with self._lock:
            session = self._sessions.get(session_id)
            if session:
                session.last_active = time.time()
            return session

    def update(self, session_id: str, data: dict):
        """更新会话数据"""
        with self._lock:
            session = self._sessions.get(session_id)
            if session:
                session.data.update(data)
                session.last_active = time.time()

    def delete(self, session_id: str):
        """删除会话"""
        with self._lock:
            self._sessions.pop(session_id, None)

    def cleanup_expired(self):
        """清理过期会话"""
        with self._lock:
            now = time.time()
            expired = [
                sid for sid, s in self._sessions.items()
                if now - s.last_active > self.ttl_seconds
            ]
            for sid in expired:
                del self._sessions[sid]

    def count(self) -> int:
        """当前会话数"""
        return len(self._sessions)


# 全局单例
_session_manager: Optional[SessionManager] = None


def get_session_manager() -> SessionManager:
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager
