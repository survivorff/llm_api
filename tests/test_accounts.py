"""v1.3 账户与登录：注册/登录、会话、自助令牌、自助账单、OAuth 会话签发。"""
from app.core.sessions import issue_session, verify_session

AUTH = {"Authorization": "Bearer ADMINKEY"}


def _register(gateway, email, password="secret123", username=None):
    return gateway.post("/auth/register", json={
        "email": email, "password": password, "username": username,
    })


# ---------------- 会话令牌单元 ----------------
def test_session_token_roundtrip():
    tok = issue_session(42, "s3cr3t", ttl=100, role="user")
    payload = verify_session(tok, "s3cr3t")
    assert payload["uid"] == 42
    assert payload["role"] == "user"
    # 错误密钥验签失败
    assert verify_session(tok, "wrong") is None
    # 篡改失败
    assert verify_session(tok[:-2] + "xx", "s3cr3t") is None


def test_session_expired():
    tok = issue_session(1, "k", ttl=-1)
    assert verify_session(tok, "k") is None


# ---------------- 注册 / 登录 ----------------
def test_register_and_login(gateway):
    r = _register(gateway, "alice@example.com")
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["user"]["email"] == "alice@example.com"
    session = data["session"]

    # 会话可用于 /auth/me
    r = gateway.get("/auth/me", headers={"Authorization": f"Bearer {session}"})
    assert r.status_code == 200
    assert r.json()["user"]["email"] == "alice@example.com"

    # 重复邮箱注册被拒
    r = _register(gateway, "alice@example.com")
    assert r.status_code == 409

    # 登录
    r = gateway.post("/auth/login", json={"email": "alice@example.com", "password": "secret123"})
    assert r.status_code == 200, r.text
    assert r.json()["user"]["email"] == "alice@example.com"

    # 错误密码
    r = gateway.post("/auth/login", json={"email": "alice@example.com", "password": "wrong"})
    assert r.status_code == 401


def test_register_validation(gateway):
    assert _register(gateway, "not-an-email").status_code == 400
    assert _register(gateway, "bob@example.com", password="123").status_code == 400


def test_me_requires_session(gateway):
    assert gateway.get("/auth/me").status_code == 401
    assert gateway.get("/auth/me", headers={"Authorization": "Bearer garbage"}).status_code == 401


# ---------------- 自助令牌 ----------------
def test_self_service_tokens(gateway):
    session = _register(gateway, "carol@example.com").json()["session"]
    h = {"Authorization": f"Bearer {session}"}

    r = gateway.post("/auth/tokens", headers=h, json={"name": "my-key"})
    assert r.status_code == 200, r.text
    key = r.json()["key"]
    assert key.startswith("sk-")
    tid = r.json()["id"]

    r = gateway.get("/auth/tokens", headers=h)
    assert r.status_code == 200
    assert any(t["id"] == tid for t in r.json()["tokens"])

    # 该令牌可用于网关转发
    r = gateway.post("/v1/chat/completions", headers={"Authorization": f"Bearer {key}"},
                     json={"model": "deepseek-chat", "messages": [{"role": "user", "content": "hi"}]})
    assert r.status_code == 200

    # 删除
    r = gateway.delete(f"/auth/tokens/{tid}", headers=h)
    assert r.status_code == 200


def test_cannot_delete_others_token(gateway):
    s1 = _register(gateway, "u1@example.com").json()["session"]
    s2 = _register(gateway, "u2@example.com").json()["session"]
    tid = gateway.post("/auth/tokens", headers={"Authorization": f"Bearer {s1}"},
                       json={"name": "k"}).json()["id"]
    # 另一个用户删不掉
    r = gateway.delete(f"/auth/tokens/{tid}",
                       headers={"Authorization": f"Bearer {s2}"})
    assert r.status_code == 404


# ---------------- 自助账单 ----------------
def test_self_service_ledger_and_orders(gateway):
    session = _register(gateway, "dave@example.com").json()["session"]
    h = {"Authorization": f"Bearer {session}"}
    # 兑换码充值后账单可见
    codes = gateway.post("/admin/redemption/generate", headers=AUTH,
                         json={"amount_credits": 100000, "count": 1}).json()["codes"]
    r = gateway.post("/pay/redeem", headers=h, json={"code": codes[0]})
    assert r.status_code == 200, r.text

    r = gateway.get("/auth/ledger", headers=h)
    assert r.status_code == 200
    assert any(e["type"] == "topup" and e["amount"] == 100000 for e in r.json()["ledger"])

    r = gateway.get("/auth/orders", headers=h)
    assert r.status_code == 200


def test_providers_listing(gateway):
    r = gateway.get("/auth/providers")
    assert r.status_code == 200
    assert "email" in r.json()
    assert "oauth" in r.json()


def test_portal_served(gateway):
    r = gateway.get("/portal")
    assert r.status_code == 200
    # 控制台含登录入口
    assert "authView" in r.text
    # 根路径是门户首页（landing）
    home = gateway.get("/")
    assert home.status_code == 200
    assert "hero" in home.text
