"""模型管理 Pydantic schemas（提示词 01 §三）"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

ProviderCode = Literal[
    "openai",
    "anthropic",
    "deepseek",
    "moonshot",
    "zhipu",
    "minimax",
    "volcengine",
    "qianfan",
    "ollama",
    "custom",
    "dashscope",
]
ModelKind = Literal["chat", "embedding", "rerank"]
Distance = Literal["cosine", "l2", "inner_product"]


class ModelProviderBase(BaseModel):
    code: ProviderCode
    display_name: str = Field(min_length=1, max_length=64)
    base_url: str = Field(min_length=1, max_length=512)
    enabled: bool = True


class ModelProviderCreate(ModelProviderBase):
    pass


class ModelProviderUpdate(BaseModel):
    display_name: str | None = Field(default=None, max_length=64)
    base_url: str | None = Field(default=None, max_length=512)
    enabled: bool | None = None


class ModelProviderResponse(ModelProviderBase):
    created_at: datetime | None = None
    updated_at: datetime | None = None
    model_config = {"from_attributes": True}


class ModelBase(BaseModel):
    provider_code: ProviderCode
    model_name: str = Field(min_length=1, max_length=128)
    kind: ModelKind
    parameters: dict[str, object] = Field(default_factory=dict)
    enabled: bool = True


class ModelCreate(ModelBase):
    api_key: str | None = Field(default=None, description="明文密钥，仅写入")
    dimensions: int | None = Field(default=None, ge=1, le=4096)
    distance: Distance | None = None
    top_n: int | None = Field(default=None, ge=1, le=1000)


class ModelUpdate(BaseModel):
    model_name: str | None = Field(default=None, max_length=128)
    parameters: dict[str, object] | None = None
    api_key: str | None = Field(default=None, description="明文密钥；空字符串表示清空")
    enabled: bool | None = None
    dimensions: int | None = Field(default=None, ge=1, le=4096)
    distance: Distance | None = None
    top_n: int | None = Field(default=None, ge=1, le=1000)


class ModelResponse(ModelBase):
    id: str
    api_key_set: bool = Field(default=False, description="仅表示是否已设置密钥")
    dimensions: int | None = None
    distance: Distance | None = None
    top_n: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    model_config = {"from_attributes": True}


class TestModelResponse(BaseModel):
    ok: bool
    latency_ms: int
    model_info: dict[str, object] | None = None
    error_code: str | None = None
    error_message: str | None = None
