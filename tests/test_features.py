import time

ADMIN = {"Authorization": "Bearer ADMINKEY"}


def _make(gateway, **body):
    return gateway.post("/admin/tokens", headers=ADMIN, json=body).json()


def test_expired_token_rejected(gateway):
    tok = _make(gateway, name="expired", expires_at=time.time() - 10)
    r = gateway.post("/v1/chat/completions",
                     headers={"Authorization": f"Bearer {tok['key']}"},
                     json={"model": "deepseek-chat", "messages": []})
    assert r.status_code == 401


def test_expires_in_days_sets_future(gateway):
    tok = _make(gateway, name="future", expires_in_days=30)
    assert tok["expires_at"] > time.time()
    r = gateway.post("/v1/chat/completions",
                     headers={"Authorization": f"Bearer {tok['key']}"},
                     json={"model": "deepseek-chat", "messages": []})
    assert r.status_code == 200


def test_rpm_limit(gateway):
    tok = _make(gateway, name="fast", rpm_limit=1)
    h = {"Authorization": f"Bearer {tok['key']}"}
    body = {"model": "deepseek-chat", "messages": []}
    assert gateway.post("/v1/chat/completions", headers=h, json=body).status_code == 200
    assert gateway.post("/v1/chat/completions", headers=h, json=body).status_code == 429


def test_model_allow_list(gateway):
    tok = _make(gateway, name="limited", allowed_models="deepseek-chat")
    h = {"Authorization": f"Bearer {tok['key']}"}
    assert gateway.post("/v1/chat/completions", headers=h,
                        json={"model": "deepseek-chat", "messages": []}).status_code == 200
    assert gateway.post("/v1/chat/completions", headers=h,
                        json={"model": "claude", "messages": []}).status_code == 403


def test_self_service_me(gateway):
    tok = _make(gateway, name="selfcheck", quota_tokens=1000)
    r = gateway.get("/v1/me", headers={"Authorization": f"Bearer {tok['key']}"})
    assert r.status_code == 200
    data = r.json()
    assert data["name"] == "selfcheck"
    assert data["remaining_tokens"] == 1000


def test_streaming_usage_counted(gateway):
    tok = _make(gateway, name="streamer")
    h = {"Authorization": f"Bearer {tok['key']}"}
    with gateway.stream("POST", "/v1/chat/completions", headers=h,
                        json={"model": "deepseek-chat", "stream": True,
                              "messages": [{"role": "user", "content": "hi"}]}) as r:
        assert r.status_code == 200
        b"".join(r.iter_bytes())
    # 流式 usage 应被计入该令牌（mock 末尾返回 total_tokens=7）
    me = gateway.get("/v1/me", headers=h).json()
    assert me["used_tokens"] == 7
