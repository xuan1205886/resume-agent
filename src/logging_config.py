"""
统一日志配置 — 全局 logging 设置，支持控制台和文件输出
在应用启动时调用 setup_logging() 配置全局日志
"""

import logging
import os
import sys
from pathlib import Path


def setup_logging(
    level: str = "INFO",
    log_file: str = "",
    log_format: str = "",
) -> None:
    """配置全局日志系统

    Args:
        level: 日志级别 (DEBUG/INFO/WARNING/ERROR)
        log_file: 日志文件路径（为空则只输出到控制台）
        log_format: 自定义日志格式（为空使用默认格式）
    """
    if not log_format:
        log_format = "%(asctime)s [%(levelname)-5s] %(name)s: %(message)s"

    date_format = "%Y-%m-%d %H:%M:%S"

    # 获取根 logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # 清除已有 handler（避免重复）
    root_logger.handlers.clear()

    # 控制台 handler（Windows GBK 环境下处理 Unicode 字符）
    try:
        # 尝试用 utf-8 包装 stdout，避免中文/emoji 导致的 UnicodeEncodeError
        import io
        utf8_stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        console_handler = logging.StreamHandler(utf8_stdout)
    except Exception:
        console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(logging.Formatter(log_format, datefmt=date_format))
    root_logger.addHandler(console_handler)

    # 文件 handler（可选）
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(logging.Formatter(log_format, datefmt=date_format))
        root_logger.addHandler(file_handler)

    # 降低第三方库的日志级别（避免噪音）
    for lib in ["chromadb", "sentence_transformers", "transformers", "urllib3", "httpx", "openai"]:
        logging.getLogger(lib).setLevel(logging.WARNING)

    root_logger.info(f"日志系统初始化完成 (level={level})")


def get_log_level_from_env() -> str:
    """从环境变量获取日志级别"""
    return os.getenv("LOG_LEVEL", "INFO").upper()
