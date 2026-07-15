"""
多供应商 LLM 封装 — 统一 LangChain BaseChatModel 接口

支持供应商：
  - deepseek  : DeepSeek API（OpenAI 兼容）
  - openai    : OpenAI API（GPT-4o / GPT-4 等）
  - anthropic : Anthropic Claude API
  - ollama    : 本地 Ollama 模型

所有下游代码只需调用 get_llm(temperature=0.3)，无需关心供应商细节。
运行时通过 config.yaml → llm.provider 切换。
"""

import enum
import logging
import time
from typing import Any, Iterator, List, Optional

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, AIMessageChunk, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatGenerationChunk, ChatResult
from pydantic import Field

from src.config import get_config

logger = logging.getLogger("llm")

# 可重试的 HTTP 状态码
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


class LLMProvider(str, enum.Enum):
    """LLM 供应商枚举"""
    DEEPSEEK = "deepseek"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    OLLAMA = "ollama"

    def is_openai_compatible(self) -> bool:
        """是否使用 OpenAI 兼容客户端"""
        return self in (LLMProvider.DEEPSEEK, LLMProvider.OPENAI)


def _retry_with_backoff(
    func,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
):
    """通用重试装饰器，带指数退避

    Args:
        func: 要执行的函数
        max_retries: 最大重试次数
        base_delay: 初始退避延迟（秒）
        max_delay: 最大退避延迟（秒）

    Returns:
        函数执行结果

    Raises:
        最后一次执行的异常（如果所有重试都失败）
    """
    last_exception = None
    for attempt in range(max_retries + 1):
        try:
            return func()
        except Exception as e:
            last_exception = e
            error_str = str(e)

            # 判断是否可重试
            is_rate_limited = "429" in error_str or "rate" in error_str.lower()
            is_server_error = any(
                str(code) in error_str for code in RETRYABLE_STATUS_CODES
            )
            is_connection_error = "connection" in error_str.lower() or "timeout" in error_str.lower()

            retryable = is_rate_limited or is_server_error or is_connection_error

            if attempt < max_retries and retryable:
                delay = min(base_delay * (2 ** attempt), max_delay)
                logger.warning(
                    f"LLM 调用失败 (尝试 {attempt + 1}/{max_retries + 1}): {error_str[:200]}。"
                    f"{'可重试' if retryable else '不可重试'}，{delay:.1f}s 后重试..."
                )
                time.sleep(delay)
            elif attempt < max_retries and not retryable:
                logger.error(f"LLM 调用失败（不可重试错误）: {error_str[:200]}")
                raise
            else:
                logger.error(f"LLM 调用失败（已达最大重试次数 {max_retries}）: {error_str[:200]}")
                raise

    raise last_exception  # 不应该到达这里


class MultiProviderChatModel(BaseChatModel):
    """多供应商 LLM 的 LangChain 兼容封装（带重试和超时）

    根据 provider 参数自动选择底层客户端：
      - deepseek/openai → openai.OpenAI 客户端
      - anthropic       → anthropic.Anthropic 客户端
      - ollama          → ollama.Client 客户端
    """

    provider: str = "deepseek"
    model_name: str = "deepseek-chat"
    temperature: float = 0.3
    max_tokens: int = 2048
    request_timeout: int = 60
    max_retries: int = 3
    base_url: str = ""
    client: Any = None

    # 允许非 Pydantic 字段的客户端对象
    model_config = {"arbitrary_types_allowed": True, "extra": "allow"}

    def __init__(self, **kwargs):
        config = get_config()

        # 先从 kwargs 提取 provider 相关信息（存在局部变量中，避免在 super().__init__ 前操作 self）
        provider_str = kwargs.pop("provider", config.llm.provider)
        try:
            _provider = LLMProvider(provider_str)
        except ValueError:
            logger.warning(f"未知 provider '{provider_str}'，回退到 deepseek")
            _provider = LLMProvider.DEEPSEEK

        kwargs.setdefault("model_name", config.llm.model)
        kwargs.setdefault("temperature", config.llm.temperature)
        kwargs.setdefault("max_tokens", config.llm.max_tokens)
        kwargs.setdefault("request_timeout", config.llm.request_timeout)
        kwargs.setdefault("max_retries", config.llm.max_retries)
        kwargs.setdefault("base_url", config.llm.base_url)

        # Pydantic 初始化（此之后才能设置 self 上的自定义属性）
        super().__init__(**kwargs)

        # 设置非 Pydantic 字段（_ 前缀为私有属性，Pydantic 忽略）
        self._provider_str = provider_str
        self._provider = _provider
        # Pydantic 允许的字段更新
        self.client = None  # 将在 _init_client 中替换为实际客户端
        self._init_client(config)

    def _init_client(self, config):
        """根据 provider 初始化对应的客户端"""
        if self._provider.is_openai_compatible():
            from openai import OpenAI
            self.client = OpenAI(
                api_key=config.llm.api_key,
                base_url=self.base_url,
                timeout=self.request_timeout,
                max_retries=0,  # 我们自己管理重试
            )
        elif self._provider == LLMProvider.ANTHROPIC:
            from anthropic import Anthropic
            api_key = config.llm.api_key
            if not api_key:
                raise ValueError(
                    "使用 Anthropic 需要设置 ANTHROPIC_API_KEY 环境变量"
                )
            self.client = Anthropic(
                api_key=api_key,
                timeout=self.request_timeout,
                max_retries=0,
            )
        elif self._provider == LLMProvider.OLLAMA:
            from ollama import Client
            self.client = Client(
                host=self.base_url or "http://localhost:11434",
                timeout=self.request_timeout,
            )

    @property
    def _llm_type(self) -> str:
        return f"{self._provider_str}-chat"

    @property
    def _identifying_params(self) -> dict:
        return {
            "provider": self._provider_str,
            "model_name": self.model_name,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "request_timeout": self.request_timeout,
            "max_retries": self.max_retries,
            "base_url": self.base_url,
        }

    def _convert_messages(self, messages: List[BaseMessage]) -> List[dict]:
        """将 LangChain 消息转为各供应商通用格式"""
        converted = []
        for msg in messages:
            if msg.type == "system":
                converted.append({"role": "system", "content": msg.content})
            elif msg.type == "human":
                converted.append({"role": "user", "content": msg.content})
            elif msg.type == "ai":
                converted.append({"role": "assistant", "content": msg.content})
            else:
                converted.append({"role": "user", "content": str(msg.content)})
        return converted

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> ChatResult:
        """同步生成（带自动重试，按 provider 分发）"""

        def _call():
            if self._provider.is_openai_compatible():
                return self._call_openai(messages, stop)
            elif self._provider == LLMProvider.ANTHROPIC:
                return self._call_anthropic(messages, stop)
            elif self._provider == LLMProvider.OLLAMA:
                return self._call_ollama(messages, stop)
            else:
                raise ValueError(f"未知 provider: {self._provider_str}")

        return _retry_with_backoff(
            _call,
            max_retries=self.max_retries,
            base_delay=1.0,
            max_delay=30.0,
        )

    def _call_openai(self, messages: List[BaseMessage], stop: Optional[List[str]] = None) -> ChatResult:
        """OpenAI 兼容 API 调用（DeepSeek / OpenAI）"""
        openai_messages = self._convert_messages(messages)
        params = {
            "model": self.model_name,
            "messages": openai_messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "stream": False,
        }
        if stop:
            params["stop"] = stop

        response = self.client.chat.completions.create(**params)
        choice = response.choices[0]
        content = choice.message.content or ""

        generation = ChatGeneration(
            message=AIMessage(content=content),
            generation_info={
                "finish_reason": choice.finish_reason,
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                    "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                },
            },
        )
        return ChatResult(generations=[generation])

    def _call_anthropic(self, messages: List[BaseMessage], stop: Optional[List[str]] = None) -> ChatResult:
        """Anthropic Claude API 调用"""
        # Anthropic 要求 system 消息单独提取
        system_prompt = ""
        user_messages = []
        for msg in messages:
            if msg.type == "system":
                system_prompt = str(msg.content)
            else:
                converted = self._convert_messages([msg])
                if converted:
                    user_messages.append(converted[0])

        params = {
            "model": self.model_name,
            "messages": user_messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }
        if system_prompt:
            params["system"] = system_prompt
        if stop:
            params["stop_sequences"] = stop

        response = self.client.messages.create(**params)
        # Anthropic 返回的 content 可能是列表
        content = ""
        if response.content:
            if isinstance(response.content, list):
                content = "".join(
                    block.text if hasattr(block, "text") else str(block)
                    for block in response.content
                )
            else:
                content = str(response.content)

        generation = ChatGeneration(
            message=AIMessage(content=content),
            generation_info={
                "finish_reason": response.stop_reason or "",
                "usage": {
                    "prompt_tokens": response.usage.input_tokens if response.usage else 0,
                    "completion_tokens": response.usage.output_tokens if response.usage else 0,
                },
            },
        )
        return ChatResult(generations=[generation])

    def _call_ollama(self, messages: List[BaseMessage], stop: Optional[List[str]] = None) -> ChatResult:
        """Ollama 本地模型调用"""
        ollama_messages = self._convert_messages(messages)
        options = {
            "temperature": self.temperature,
            "num_predict": self.max_tokens,
        }
        if stop:
            options["stop"] = stop

        response = self.client.chat(
            model=self.model_name,
            messages=ollama_messages,
            options=options,
            stream=False,
        )

        content = response.get("message", {}).get("content", "")

        generation = ChatGeneration(
            message=AIMessage(content=content),
            generation_info={
                "finish_reason": response.get("done_reason", ""),
                "usage": {
                    "prompt_tokens": response.get("prompt_eval_count", 0),
                    "completion_tokens": response.get("eval_count", 0),
                },
            },
        )
        return ChatResult(generations=[generation])

    def _stream(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> Iterator[ChatGenerationChunk]:
        """流式生成（带自动重试，仅 OpenAI 兼容供应商支持流式）"""

        if not self._provider.is_openai_compatible():
            # Anthropic/Ollama 暂不走流式（项目当前未使用流式 LLM 调用）
            logger.debug(f"{self._provider_str} 流式生成请求，回退到非流式")
            result = self._generate(messages, stop, run_manager, **kwargs)
            content = result.generations[0].message.content
            chunk = ChatGenerationChunk(message=AIMessageChunk(content=content))
            if run_manager:
                run_manager.on_llm_new_token(content, chunk=chunk)
            yield chunk
            return

        def _call():
            openai_messages = self._convert_messages(messages)
            params = {
                "model": self.model_name,
                "messages": openai_messages,
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
                "stream": True,
            }
            if stop:
                params["stop"] = stop

            response = self.client.chat.completions.create(**params)
            return response

        response = _retry_with_backoff(
            _call,
            max_retries=self.max_retries,
            base_delay=1.0,
        )

        for chunk in response:
            if chunk.choices and chunk.choices[0].delta.content:
                content = chunk.choices[0].delta.content
                chunk_obj = ChatGenerationChunk(
                    message=AIMessageChunk(content=content)
                )
                if run_manager:
                    run_manager.on_llm_new_token(content, chunk=chunk_obj)
                yield chunk_obj


def get_llm(**kwargs) -> MultiProviderChatModel:
    """获取 LLM 实例（工厂函数）

    下游调用示例：
        llm = get_llm(temperature=0.1)
        llm = get_llm(temperature=0.3, max_tokens=4096)

    优先级：kwargs > config.yaml

    返回值始终是 MultiProviderChatModel，实现 LangChain BaseChatModel 接口，
    支持 .invoke(messages) 和 .stream(messages)。
    """
    return MultiProviderChatModel(**kwargs)
