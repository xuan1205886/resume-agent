"""
LLM 输出校验器 — 从 LLM 返回中提取 JSON、校验 Schema、失败时重试
解决 JSON 解析失败静默吞掉的问题
"""

import json
import logging
from typing import Type, TypeVar

from pydantic import BaseModel, ValidationError

logger = logging.getLogger("output_validator")

T = TypeVar("T", bound=BaseModel)

# JSON 解析最大重试次数（不含 LLM 调用）
MAX_JSON_PARSE_RETRIES = 2


class LLMOutputError(Exception):
    """LLM 输出无法解析或校验失败"""

    def __init__(self, message: str, raw_content: str = "", parse_errors: list[str] = None):
        super().__init__(message)
        self.raw_content = raw_content
        self.parse_errors = parse_errors or []


def _find_json_boundary(content: str, open_c: str, close_c: str) -> tuple:
    """找到 JSON 最外层括号的起止位置，跳过字符串内的同类型括号"""
    start = -1
    depth = 0
    in_string = False
    escape_next = False

    for i, ch in enumerate(content):
        if escape_next:
            escape_next = False
            continue
        if ch == '\\':
            escape_next = True
            continue
        if ch == '"' and not escape_next:
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == open_c:
            if depth == 0:
                start = i
            depth += 1
        elif ch == close_c:
            depth -= 1
            if depth == 0 and start != -1:
                return (start, i)

    return (start, -1)


def extract_json_from_text(content: str) -> str:
    """从 LLM 返回的文本中提取并修复 JSON 字符串

    处理：
    1. Markdown 代码块（```json ... ```）
    2. 前导/尾随非 JSON 文本（跳过字符串内的花括号）
    3. 尾部逗号
    4. 单引号 JSON
    """
    import re
    original = content.strip()  # 保存原始内容用于 retry

    # 1. 移除 markdown 代码块包装
    content = re.sub(r'^```(?:json)?\s*\n?', '', original, flags=re.IGNORECASE)
    content = re.sub(r'\n?```\s*$', '', content)

    # 2. 使用 JSON-aware 状态机提取最外层括号范围
    for open_c, close_c in [('{', '}'), ('[', ']')]:
        start, end = _find_json_boundary(content, open_c, close_c)
        if start != -1 and end != -1 and end > start:
            content = content[start:end + 1]
            break

    # 3. 修复尾部逗号（,} → }   ,] → ]）
    content = re.sub(r',\s*([}\]])', r'\1', content)

    # 4. 修复明显的单引号 JSON（只替换 key 周围的引号）
    if content.count("'") > content.count('"'):
        # 替换 '"key" 模式周围的单引号
        content = re.sub(r"'([^\"']+)'(?=\s*:)", r'"\1"', content)
        # 替换 :'value' 模式周围的单引号
        content = re.sub(r"(?<=:\s*)'([^\"']*)'", r'"\1"', content)

    return content.strip()


def parse_and_validate(
    content: str,
    schema: Type[T],
    context: str = "",
) -> T:
    """解析 LLM 输出为 JSON 并校验 Schema

    Args:
        content: LLM 原始返回文本
        schema: Pydantic 模型类
        context: 上下文描述（用于错误日志）

    Returns:
        校验通过的 Pydantic 模型实例

    Raises:
        LLMOutputError: JSON 解析失败或 Schema 校验失败
    """
    errors: list[str] = []
    original_content = content  # 保存原始输出，retry 时始终从原始重新提取

    for attempt in range(MAX_JSON_PARSE_RETRIES + 1):
        try:
            json_str = extract_json_from_text(content)
            data = json.loads(json_str)

            # 如果 data 是列表，取第一个元素
            if isinstance(data, list) and len(data) > 0:
                data = data[0]

            if not isinstance(data, dict):
                raise LLMOutputError(
                    f"{context}: LLM 返回的不是 JSON 对象（类型: {type(data).__name__}）",
                    raw_content=content,
                    parse_errors=[f"期望 dict，实际为 {type(data).__name__}"],
                )

            validated = schema(**data)
            return validated

        except json.JSONDecodeError as e:
            errors.append(f"JSON 解析失败 (尝试 {attempt + 1}): {e}")
            if attempt < MAX_JSON_PARSE_RETRIES:
                # 从原始内容重新提取（而非重复清洗已处理过的内容）
                content = original_content
            else:
                raise LLMOutputError(
                    f"{context}: JSON 解析失败，经过 {MAX_JSON_PARSE_RETRIES + 1} 次尝试",
                    raw_content=original_content,
                    parse_errors=errors,
                )

        except ValidationError as e:
            errors.append(f"Schema 校验失败: {e}")
            raise LLMOutputError(
                f"{context}: 输出格式校验失败 — {e}",
                raw_content=content,
                parse_errors=errors,
            )

    # 不应到达这里
    raise LLMOutputError(f"{context}: 解析失败", raw_content=content, parse_errors=errors)
