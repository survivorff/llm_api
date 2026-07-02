"""v1.1 协议适配器与多端点测试：Claude / Gemini 互转、embeddings、Anthropic 原生入口。"""
import json

AUTH = {"Authorization": "Bearer ADMINKEY"}


def _mock_base(gateway) -> str:
    """读取已有 mock 渠道的 base_url（形如 http://127.0.0.1:PORT/v1）。"""
    chans = gateway.get("/admin/channels", headers=AUTH).json()["channels"]
    for c in chans:
        if c["name"] == "mock-deepseek":
            return c["base_url"]
    raise AssertionError("mock-deepseek channel not found")


def _add_channel(gateway, name, ctype, models, base_url=None):
    """通过 admin API 建渠道。base_url 默认复用 mock 上游。"""
    base = base_url or _mock_base(gateway)
    r = gateway.post("/admin/channels", headers=AUTH, json={
        "name": name, "type": ctype, "base_url": base,
        "api_keys": ["GOOD_KEY"], "models": models,
    })
    assert r.status_code == 200, r.text
    return r.json()


def test_claude_adapter_nonstream(gateway):
    _add_channel(gateway, "mock-claude", "claude", ["claude-3-5-sonnet"])
    r = gateway.post("/v1/chat/completions", headers=AUTH, json={
        "model": "claude-3-5-sonnet",
        "messages": [{"role": "system", "content": "be brief"},
                     {"role": "user", "content": "hi"}],
    })
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["choices"][0]["message"]["content"] == "claude-echo:claude-3-5-sonnet"
    assert body["usage"]["total_tokens"] == 8  # 5 in + 3 out


def test_claude_adapter_stream(gateway):
    _add_channel(gateway, "mock-claude2", "claude", ["claude-stream"])
    with gateway.stream("POST", "/v1/chat/completions", headers=AUTH, json={
        "model": "claude-stream", "stream": True,
        "messages": [{"role": "user", "content": "hi"}],
    }) as r:
        assert r.status_code == 200
        body = b"".join(r.iter_bytes())
    assert b"Hi" in body
    assert b"[DONE]" in body
    assert b"chat.completion.chunk" in body


def test_gemini_adapter_nonstream(gateway):
    # Gemini 上游路径是 {base}/models/{model}:generateContent，mock 挂在 /v1beta
    base = _mock_base(gateway).rsplit("/v1", 1)[0] + "/v1beta"
    _add_channel(gateway, "mock-gemini", "gemini", ["gemini-1.5-pro"], base_url=base)
    r = gateway.post("/v1/chat/completions", headers=AUTH, json={
        "model": "gemini-1.5-pro",
        "messages": [{"role": "user", "content": "hi"}],
    })
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["choices"][0]["message"]["content"] == "gemini-echo:gemini-1.5-pro"
    assert body["usage"]["total_tokens"] == 8


def test_embeddings(gateway):
    _add_channel(gateway, "mock-embed", "openai", ["text-embedding-3-small"])
    r = gateway.post("/v1/embeddings", headers=AUTH, json={
        "model": "text-embedding-3-small", "input": ["a", "b"],
    })
    assert r.status_code == 200, r.text
    assert len(r.json()["data"]) == 2


def test_anthropic_native_endpoint(gateway):
    """/v1/messages 原生入口 → 统一表示 → 转发。上游用 openai mock 渠道。"""
    r = gateway.post("/v1/messages", headers=AUTH, json={
        "model": "deepseek-chat",
        "system": "be brief",
        "messages": [{"role": "user", "content": [{"type": "text", "text": "hi"}]}],
        "max_tokens": 100,
    })
    assert r.status_code == 200, r.text
    # 统一表示走 openai mock，返回 echo
    assert "echo" in json.dumps(r.json())
