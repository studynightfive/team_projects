"""模型管理写接口响应回归测试。"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.api import patch_model_endpoint
from app.models.repository import Model
from app.models.schemas import ModelUpdate


@pytest.mark.asyncio
async def test_patch_model_refreshes_server_fields_before_response() -> None:
    now = datetime.now(timezone.utc)
    model = Model(
        id="model-1",
        provider_code="deepseek",
        model_name="deepseek-v4-pro",
        kind="chat",
        parameters={"temperature": 0.2, "max_tokens": 1200},
        enabled=False,
    )
    model.created_at = now
    model.updated_at = now
    db = AsyncMock(spec=AsyncSession)
    user = MagicMock(id="admin-user")
    request = Request(
        {
            "type": "http",
            "method": "PATCH",
            "path": "/api/v1/models/model-1",
            "headers": [],
            "query_string": b"",
            "client": ("127.0.0.1", 12345),
            "server": ("test", 80),
            "scheme": "http",
        }
    )

    with (
        patch(
            "app.models.api.service.update_model",
            new=AsyncMock(return_value=model),
        ),
        patch("app.models.api.audit", new=AsyncMock()),
    ):
        response = await patch_model_endpoint(
            "model-1",
            request,
            ModelUpdate(enabled=False),
            user,
            None,
            db,
        )

    assert db.commit.await_count == 2
    db.refresh.assert_awaited_once_with(model)
    assert response["data"]["updated_at"] == now
    assert response["data"]["enabled"] is False
