"""v2.3 渠道账号池：key 池摘要、单 key 启停、连通性测试、模型发现、分组聚合。"""
AUTH = {"Authorization": "Bearer ADMINKEY"}


def _mock_base(gateway):
    for c in gateway.get("/admin/channels", headers=AUTH).json()["channels"]:
        if c["name"] == "mock-deepseek":
            return c["base_url"]
    raise AssertionError("mock channel missing")


def test_channel_keys_summary(gateway):
    # mock-fallback 有两个 key（BAD_KEY, GOOD_KEY）
    chans = gateway.get("/admin/channels", headers=AUTH).json()["channels"]
    fb = next(c for c in chans if c["name"] == "mock-fallback")
    r = gateway.get(f"/admin/channels/{fb['id']}/keys", headers=AUTH)
    assert r.status_code == 200
    keys = r.json()["keys"]
    assert len(keys) == 2
    # 脱敏：不含完整明文，含指纹与掩码
    for k in keys:
        assert "fp" in k and "masked" in k and "····" in k["masked"]


def test_channel_key_toggle(gateway):
    """禁用某 key 后，key 摘要显示 disabled；重新启用恢复。"""
    chans = gateway.get("/admin/channels", headers=AUTH).json()["channels"]
    ds = next(c for c in chans if c["name"] == "mock-deepseek")
    keys = gateway.get(f"/admin/channels/{ds['id']}/keys", headers=AUTH).json()["keys"]
    fp = keys[0]["fp"]
    assert keys[0]["disabled"] is False

    r = gateway.post(f"/admin/channels/{ds['id']}/keys/{fp}/toggle", headers=AUTH,
                     json={"disabled": True})
    assert r.status_code == 200 and r.json()["disabled"] is True
    keys2 = gateway.get(f"/admin/channels/{ds['id']}/keys", headers=AUTH).json()["keys"]
    assert keys2[0]["disabled"] is True

    # 恢复
    gateway.post(f"/admin/channels/{ds['id']}/keys/{fp}/toggle", headers=AUTH,
                 json={"disabled": False})
    keys3 = gateway.get(f"/admin/channels/{ds['id']}/keys", headers=AUTH).json()["keys"]
    assert keys3[0]["disabled"] is False


def test_disabled_key_skipped_in_routing(gateway):
    """禁用单 key 渠道的唯一 key 后，该模型应无渠道(404)。"""
    base = _mock_base(gateway)
    # 先停用通配 catchall，避免它兜底
    for c in gateway.get("/admin/channels", headers=AUTH).json()["channels"]:
        if c["name"] == "mock-catchall":
            gateway.patch(f"/admin/channels/{c['id']}", headers=AUTH, json={"status": 0})
    ch = gateway.post("/admin/channels", headers=AUTH, json={
        "name": "solo", "type": "openai", "base_url": base,
        "api_keys": ["GOOD_KEY"], "models": ["solo-only-model"],
    }).json()
    tok = gateway.post("/admin/tokens", headers=AUTH, json={"name": "t2"}).json()["key"]
    h = {"Authorization": f"Bearer {tok}"}
    ok = gateway.post("/v1/chat/completions", headers=h,
                      json={"model": "solo-only-model", "messages": [{"role": "user", "content": "hi"}]})
    assert ok.status_code == 200
    fp = gateway.get(f"/admin/channels/{ch['id']}/keys", headers=AUTH).json()["keys"][0]["fp"]
    gateway.post(f"/admin/channels/{ch['id']}/keys/{fp}/toggle", headers=AUTH, json={"disabled": True})
    resp = gateway.post("/v1/chat/completions", headers=h,
                        json={"model": "solo-only-model", "messages": [{"role": "user", "content": "hi"}]})
    assert resp.status_code == 404


def test_channel_test_endpoint(gateway):
    chans = gateway.get("/admin/channels", headers=AUTH).json()["channels"]
    ds = next(c for c in chans if c["name"] == "mock-deepseek")
    r = gateway.post(f"/admin/channels/{ds['id']}/test", headers=AUTH, json={})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["model"] == "deepseek-chat"
    assert len(body["results"]) == 1
    assert body["results"][0]["ok"] is True
    # 测试后 key 统计应有记录
    keys = gateway.get(f"/admin/channels/{ds['id']}/keys", headers=AUTH).json()["keys"]
    assert keys[0]["ok"] >= 1


def test_channel_test_all_keys(gateway):
    chans = gateway.get("/admin/channels", headers=AUTH).json()["channels"]
    fb = next(c for c in chans if c["name"] == "mock-fallback")
    r = gateway.post(f"/admin/channels/{fb['id']}/test", headers=AUTH, json={"all_keys": True})
    assert r.status_code == 200
    results = r.json()["results"]
    assert len(results) == 2
    # BAD_KEY 应失败，GOOD_KEY 应成功
    oks = {rr["ok"] for rr in results}
    assert True in oks and False in oks


def test_discover_models(gateway):
    chans = gateway.get("/admin/channels", headers=AUTH).json()["channels"]
    ds = next(c for c in chans if c["name"] == "mock-deepseek")
    r = gateway.get(f"/admin/channels/{ds['id']}/discover-models", headers=AUTH)
    assert r.status_code == 200, r.text
    assert "deepseek-chat" in r.json()["models"]


def test_groups_aggregation(gateway):
    # 造一个非 default 分组用户
    gateway.post("/admin/users", headers=AUTH, json={"username": "vip1", "group": "vip"})
    r = gateway.get("/admin/groups", headers=AUTH)
    assert r.status_code == 200
    groups = {g["group"]: g for g in r.json()["groups"]}
    assert "vip" in groups
    assert groups["vip"]["users"] >= 1
