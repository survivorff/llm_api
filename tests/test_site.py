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
