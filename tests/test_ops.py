"""v2.0 运营与可观测：运营设置热更新、公开设置、Prometheus 指标、审计日志。"""
AUTH = {"Authorization": "Bearer ADMINKEY"}


def test_public_settings_defaults(gateway):
    r = gateway.get("/public/settings")
    assert r.status_code == 200
    data = r.json()
    assert "announcement" in data
    assert "site_name" in data
    assert "default_language" in data


def test_settings_hot_update(gateway):
    # 更新公告与站点名
    r = gateway.put("/admin/settings", headers=AUTH,
                    json={"announcement": "维护通知", "site_name": "MyGW"})
    assert r.status_code == 200, r.text
    assert r.json()["settings"]["announcement"] == "维护通知"

    # 公开端点立即可见（缓存写后失效）
    r = gateway.get("/public/settings")
    assert r.json()["announcement"] == "维护通知"
    assert r.json()["site_name"] == "MyGW"


def test_settings_update_requires_admin(gateway):
    r = gateway.put("/admin/settings", json={"site_name": "x"})
    assert r.status_code in (401, 403)


def test_settings_empty_payload_rejected(gateway):
    r = gateway.put("/admin/settings", headers=AUTH, json={})
    assert r.status_code == 400


def test_audit_records_settings_change(gateway):
    gateway.put("/admin/settings", headers=AUTH, json={"topup_min": 5})
    r = gateway.get("/admin/audit", headers=AUTH)
    assert r.status_code == 200
    logs = r.json()["logs"]
    assert any(log["action"] == "settings.update" for log in logs)


def test_audit_filter_by_action(gateway):
    gateway.put("/admin/settings", headers=AUTH, json={"site_name": "z"})
    r = gateway.get("/admin/audit?action=settings.update", headers=AUTH)
    assert r.status_code == 200
    assert all(log["action"] == "settings.update" for log in r.json()["logs"])


def test_metrics_endpoint(gateway):
    # 先打一次转发产生指标
    tok = gateway.post("/admin/tokens", headers=AUTH, json={"name": "m"}).json()["key"]
    gateway.post("/v1/chat/completions", headers={"Authorization": f"Bearer {tok}"},
                 json={"model": "deepseek-chat", "messages": [{"role": "user", "content": "hi"}]})
    r = gateway.get("/metrics")
    assert r.status_code == 200
    body = r.text
    assert "llm_api_requests_total" in body
    assert "# TYPE llm_api_requests_total counter" in body


def test_metrics_unit():
    from app.core import metrics
    metrics.reset()
    metrics.inc_counter("llm_api_requests_total", endpoint="chat", status=200)
    metrics.inc_counter("llm_api_requests_total", endpoint="chat", status=200)
    metrics.observe_latency("llm_api_request_duration_seconds", 0.3, endpoint="chat")
    out = metrics.render()
    assert "llm_api_requests_total" in out
    assert "llm_api_request_duration_seconds_bucket" in out
    assert 'le="+Inf"' in out
    assert "_count" in out
