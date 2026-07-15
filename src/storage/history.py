"""
历史记录 — SQLite 存储每次分析结果
"""

import json
import logging
import sqlite3
import time
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger("history")

DB_PATH = Path(__file__).parent.parent.parent / "data" / "history.db"


def _get_conn() -> sqlite3.Connection:
    """获取数据库连接（自动创建表）"""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    _init_tables(conn)
    return conn


def _init_tables(conn: sqlite3.Connection):
    """初始化表结构"""
    # 启用 WAL 模式，支持并发读写
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS analysis_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            jd_text TEXT,
            jd_position TEXT,
            overall_score REAL,
            optimized_resume_md TEXT,
            fact_check_json TEXT,
            match_results_json TEXT,
            suggestions_json TEXT,
            interview_questions_json TEXT,
            learning_plan_md TEXT
        )
    """)
    conn.commit()


def save_analysis(result: dict):
    """保存一次分析结果

    Args:
        result: SSE done 事件的 data 字段内容
    """
    try:
        conn = _get_conn()
        conn.execute("""
            INSERT INTO analysis_history
            (created_at, jd_text, jd_position, overall_score,
             optimized_resume_md, fact_check_json, match_results_json,
             suggestions_json, interview_questions_json, learning_plan_md)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            time.strftime("%Y-%m-%d %H:%M:%S"),
            result.get("jd_summary", ""),
            result.get("jd_position", ""),
            result.get("overall_score", 0),
            result.get("optimized_resume_md", ""),
            json.dumps(result.get("fact_check", {}), ensure_ascii=False),
            json.dumps(result.get("match_results", []), ensure_ascii=False),
            json.dumps(result.get("suggestions", []), ensure_ascii=False),
            json.dumps(result.get("interview_questions", []), ensure_ascii=False),
            result.get("learning_plan_md", ""),
        ))
        conn.commit()
        conn.close()
        logger.info("分析结果已保存到历史记录")
    except Exception as e:
        logger.error(f"保存历史记录失败: {e}")


def get_history(limit: int = 50) -> List[dict]:
    """获取历史记录列表"""
    try:
        conn = _get_conn()
        rows = conn.execute(
            "SELECT id, created_at, jd_position, overall_score FROM analysis_history ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception as e:
        logger.error(f"获取历史记录失败: {e}")
        return []


def get_analysis_by_id(analysis_id: int) -> Optional[dict]:
    """根据 ID 获取完整的分析结果"""
    try:
        conn = _get_conn()
        row = conn.execute(
            "SELECT * FROM analysis_history WHERE id = ?", (analysis_id,)
        ).fetchone()
        conn.close()
        return dict(row) if row else None
    except Exception as e:
        logger.error(f"获取分析详情失败: {e}")
        return None
