"""
全局配置系统 — YAML + Pydantic + 环境变量叠加
复用 rag-qa-system 的配置模式
"""

import os
from pathlib import Path
from typing import Optional

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field

load_dotenv()


class AgentTokenConfig(BaseModel):
    """各 Agent 独立 token 上限（动态字段，支持任意 Agent 名称）"""
    jd_analyzer: int = 1024
    resume_parser: int = 1024
    skill_matcher: int = 1024
    suggestions: int = 1536
    bullet_reorder: int = 512
    resume_assembly: int = 4096
    fact_check: int = 2048
    interview_gen: int = 2048
    learning_plan: int = 1536

    model_config = {"extra": "allow"}  # 允许新增 Agent 的 token 配置


class LLMConfig(BaseModel):
    """LLM 配置 — 支持多供应商"""
    provider: str = "deepseek"  # deepseek | openai | anthropic | ollama
    model: str = "deepseek-chat"
    api_key_env: str = "DEEPSEEK_API_KEY"
    base_url: str = "https://api.deepseek.com"
    temperature: float = 0.3
    max_tokens: int = 2048
    request_timeout: int = 30
    max_retries: int = 2
    agent_max_tokens: AgentTokenConfig = Field(default_factory=AgentTokenConfig)

    # 运行时注入（支持多供应商自动解析）
    api_key: str = ""
    model_config = {"extra": "allow"}


# 多供应商 API Key 环境变量映射
_PROVIDER_API_KEY_ENV = {
    "deepseek": "DEEPSEEK_API_KEY",
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "ollama": None,  # Ollama 本地运行，无需 API Key
}


class EmbeddingConfig(BaseModel):
    """Embedding 模型配置"""
    model_name: str = "paraphrase-multilingual-MiniLM-L12-v2"
    device: str = "cpu"
    batch_size: int = 16


class RetrievalConfig(BaseModel):
    """检索配置"""
    top_k: int = 5
    similarity_threshold: float = 0.3
    persist_dir: str = "./chroma_db"


class RerankerConfig(BaseModel):
    """Reranker 配置"""
    model_name: str = "BAAI/bge-reranker-base"
    batch_size: int = 8
    device: str = "cpu"


class KnowledgeBaseConfig(BaseModel):
    """知识库配置"""
    persist_dir: str = "./chroma_db"
    collection_skill_taxonomy: str = "ro_skill_taxonomy"
    collection_best_practices: str = "ro_best_practices"
    collection_ats_keywords: str = "ro_ats_keywords"
    data_dir: str = "./data/kb"


class ServerConfig(BaseModel):
    """服务器配置"""
    host: str = "0.0.0.0"
    port: int = 8000
    api_key: str = ""
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:8501"])
    rate_limit_per_minute: int = 30


class ResumeConfig(BaseModel):
    """简历解析配置"""
    max_pages: int = 5
    min_text_length: int = 100


class EvalConfig(BaseModel):
    """评测配置"""
    test_cases_path: str = "./data/eval/test_cases.json"
    output_path: str = "./data/eval/results.json"
    eval_model: str = "deepseek-chat"


class AgentPipelineConfig(BaseModel):
    """Agent 流水线配置"""
    pipeline_mode: str = "parallel"  # "parallel" | "sequential"
    enable_fact_check: bool = True


class Config(BaseModel):
    """根配置"""
    llm: LLMConfig = Field(default_factory=LLMConfig)
    embedding: EmbeddingConfig = Field(default_factory=EmbeddingConfig)
    retrieval: RetrievalConfig = Field(default_factory=RetrievalConfig)
    reranker: RerankerConfig = Field(default_factory=RerankerConfig)
    knowledge_base: KnowledgeBaseConfig = Field(default_factory=KnowledgeBaseConfig)
    server: ServerConfig = Field(default_factory=ServerConfig)
    resume: ResumeConfig = Field(default_factory=ResumeConfig)
    eval: EvalConfig = Field(default_factory=EvalConfig)
    agent: AgentPipelineConfig = Field(default_factory=AgentPipelineConfig)


def load_config(config_path: Optional[str] = None) -> Config:
    """从 YAML 文件加载配置，注入环境变量"""
    if config_path is None:
        config_path = os.environ.get("CONFIG_PATH", "config.yaml")

    config_data = {}
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            config_data = yaml.safe_load(f) or {}

    config = Config(**config_data)

    # 多供应商 API Key 自动注入
    # 优先用 config.yaml 中显式指定的 api_key_env，否则按 provider 自动映射
    provider = config.llm.provider
    if config.llm.api_key_env:
        # 显式指定了环境变量名
        api_key = os.getenv(config.llm.api_key_env, "")
    elif provider in _PROVIDER_API_KEY_ENV and _PROVIDER_API_KEY_ENV[provider]:
        # 按 provider 自动查找对应的环境变量
        api_key = os.getenv(_PROVIDER_API_KEY_ENV[provider], "")
    else:
        api_key = ""

    if api_key:
        config.llm.api_key = api_key

    return config


# 模块级单例
_config: Optional[Config] = None


def get_config(config_path: Optional[str] = None) -> Config:
    """获取配置单例"""
    global _config
    if _config is None:
        _config = load_config(config_path)
    return _config


def reset_config():
    """重置配置单例（测试用）"""
    global _config
    _config = None
