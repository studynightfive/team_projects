import pytest


@pytest.mark.asyncio
async def test_swagger_ui_uses_local_assets(client) -> None:
    response = await client.get("/api/v1/docs")

    assert response.status_code == 200
    assert "/api/v1/docs-assets/vendor/swagger-ui-bundle.js" in response.text
    assert "/api/v1/docs-assets/vendor/swagger-ui.css" in response.text
    assert "/api/v1/docs-assets/swagger-initializer.js" in response.text
    assert "cdn.jsdelivr.net" not in response.text
    assert "<script>" not in response.text


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "asset_name,content_types",
    [
        (
            "swagger-ui-bundle.js",
            ("application/javascript", "text/javascript"),
        ),
        ("swagger-ui.css", ("text/css",)),
        ("favicon-32x32.png", ("image/png",)),
    ],
)
async def test_swagger_ui_local_assets_are_available(
    client,
    asset_name: str,
    content_types: tuple[str, ...],
) -> None:
    response = await client.get(f"/api/v1/docs-assets/vendor/{asset_name}")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith(content_types)


@pytest.mark.asyncio
async def test_swagger_ui_initializer_uses_local_openapi_schema(client) -> None:
    response = await client.get("/api/v1/docs-assets/swagger-initializer.js")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/javascript")
    assert 'url: "/api/v1/openapi.json"' in response.text
