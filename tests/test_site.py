"""v2.1 门户网站：首页/文档/价格页 + 公开只读端点。"""
AUTH = {"Authorization": "Bearer ADMINKEY"}


def test_home_page(gateway):
    r = gateway.get("/")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]
    # 含导航到文档/价格/控制台
    assert "/docs" in r.text and "/pricing" in r.text and "/portal" in r.text
    assert "hero" in r.text


def test_docs_page(gateway):
    r = gateway.get("/docs")
    assert r.status_code == 200
    # 不再是 FastAPI 默认 swagger
    assert "swagger" not in r.text.lower()
    assert 'id="api"' in r.text
    assert "/v1/chat/completions" in r.text


def test_pricing_page(gateway):
    r = gateway.get("/pricing")
    assert r.status_code == 200
    assert "/public/pricing" in r.text


def test_default_swagger_disabled(gateway):
    # /docs 被门户占用；openapi.json 也应关闭
    assert gateway.get("/openapi.json").status_code == 404


def test_public_models(gateway):
    # 先建一个渠道
    gateway.post("/admin/channels", headers=AUTH, json={
        "name": "ds", "type": "openai", "base_url": "http://x/v1",
        "api_keys": ["k"], "models": ["deepseek-chat", "gpt-4o"],
    })
    r = gateway.get("/public/models")
    assert r.status_code == 200
    models = {m["model"] for m in r.json()["models"]}
    assert "deepseek-chat" in models and "gpt-4o" in models
    # 不泄露 key/base_url
    assert "base_url" not in r.text and "api_key" not in r.text


def test_public_pricing(gateway):
    gateway.post("/admin/pricing", headers=AUTH, json={
        "model": "deepseek-chat", "input_price": 139, "output_price": 278,
    })
    r = gateway.get("/public/pricing")
    assert r.status_code == 200
    body = r.json()
    assert body["credits_per_usd"] > 0
    assert any(p["model"] == "deepseek-chat" for p in body["pricing"])


def test_public_pricing_hides_disabled(gateway):
    # 建一个 disabled 的定价，不应出现在公开列表
    res = gateway.post("/admin/pricing", headers=AUTH, json={
        "model": "secret-model", "input_price": 1, "output_price": 1,
    }).json()
    gateway.patch(f"/admin/pricing/{res['id']}", headers=AUTH, json={"enabled": 0})
    r = gateway.get("/public/pricing")
    models = {p["model"] for p in r.json()["pricing"]}
    assert "secret-model" not in models


def test_public_settings_exposes_base_and_email(gateway):
    r = gateway.get("/public/settings")
    assert r.status_code == 200
    body = r.json()
    assert "base_url" in body
    assert "email_auth" in body


def test_email_auth_disabled_by_default(monkeypatch, tmp_path, mock_upstream):
    """默认关闭邮箱注册/登录：register/login 返回 403，仅 OAuth。"""
    from app.config import Settings
    from app.main import create_app
    from fastapi.testclient import TestClient

    db_file = tmp_path / "noemail.db"
    settings = Settings(
        admin_key="ADMINKEY",
        database_url=f"sqlite+aiosqlite:///{db_file}",
        crypto_secret="test-crypto-secret",
        redis_url=None, legacy_config_path=None, http_trust_env=False,
        # email_auth_enabled 默认 False
    )
    app = create_app(settings)
    with TestClient(app) as client:
        assert client.get("/auth/providers").json()["email"] is False
        r = client.post("/auth/register", json={"email": "a@b.com", "password": "secret1"})
        assert r.status_code == 403
        r = client.post("/auth/login", json={"email": "a@b.com", "password": "secret1"})
        assert r.status_code == 403


def test_models_page(gateway):
    r = gateway.get("/models")
    assert r.status_code == 200
    assert "/public/models" in r.text and "/public/pricing" in r.text
    # 主题切换存在
    assert "__toggleTheme" in r.text


def test_public_stats(gateway):
    r = gateway.get("/public/stats")
    assert r.status_code == 200
    body = r.json()
    for k in ("models", "channels", "total_requests", "total_tokens"):
        assert k in body


def test_home_has_theme_and_statbar(gateway):
    r = gateway.get("/")
    assert "__toggleTheme" in r.text
    assert "statbar" in r.text
    assert "/public/stats" in r.text


def test_admin_sidebar_layout(gateway):
    r = gateway.get("/admin")
    assert r.status_code == 200
    assert 'class="sidebar"' in r.text
    assert "__toggleTheme" in r.text
