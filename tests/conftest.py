import asyncio
import json
import socket
import threading
import time

import httpx
import pytest
import uvicorn
from fastapi.testclient import TestClient

from app.config import Settings
from app.core.security import encrypt_secret
from app.db.base import get_sessionmaker
from app.db.models import Channel, ModelPricing, User
from app.main import create_app
from tests.mock_upstream import build_mock_app

TEST_CRYPTO = "test-crypto-secret"


def _free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


class _Server(uvicorn.Server):
    def install_signal_handlers(self):
        pass


@pytest.fixture(scope="session")
def mock_upstream():
    port = _free_port()
    server = _Server(uvicorn.Config(build_mock_app(), host="127.0.0.1", port=port, log_level="warning"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{port}"
    for _ in range(100):
        try:
            if httpx.get(base + "/healthz", timeout=0.5, trust_env=False).status_code == 200:
                break
        except Exception:
            time.sleep(0.05)
    else:
        raise RuntimeError("mock upstream failed to start")
    yield base + "/v1"
    server.should_exit = True
    thread.join(timeout=5)


@pytest.fixture
def gateway(mock_upstream, tmp_path):
    db_file = tmp_path / "test.db"
    settings = Settings(
        admin_key="ADMINKEY",
        database_url=f"sqlite+aiosqlite:///{db_file}",
        crypto_secret=TEST_CRYPTO,
        redis_url=None,
        legacy_config_path=None,
        http_trust_env=False,
    )
    app = create_app(settings)

    with TestClient(app) as client:
        # 启动后 lifespan 已建表 + 建 admin 用户，注入测试渠道 + 定价 + 余额
        _seed(mock_upstream)
        yield client


def _seed(mock_upstream: str):
    """向 DB 注入测试数据：3 个渠道 + 定价 + 给 admin 用户加余额。"""
    async def run():
        async with get_sessionmaker()() as s:
            enc = lambda k: encrypt_secret(k, TEST_CRYPTO)
            s.add_all([
                Channel(name="mock-deepseek", type="openai", base_url=mock_upstream,
                        api_keys=json.dumps([enc("GOOD_KEY")]),
                        models=json.dumps(["deepseek-chat"]), model_map="{}", headers="{}"),
                Channel(name="mock-fallback", type="openai", base_url=mock_upstream,
                        api_keys=json.dumps([enc("BAD_KEY"), enc("GOOD_KEY")]),
                        models=json.dumps(["fallback-model"]), model_map="{}", headers="{}"),
                Channel(name="mock-catchall", type="openai", base_url=mock_upstream,
                        api_keys=json.dumps([enc("GOOD_KEY")]),
                        models=json.dumps(["*"]),
                        model_map=json.dumps({"claude": "anthropic/claude-x"}), headers="{}"),
            ])
            # admin 用户加余额，便于计费测试
            from sqlalchemy import select
            u = (await s.execute(select(User).where(User.username == "admin"))).scalar_one()
            u.balance = 10_000_000
            await s.commit()

    asyncio.run(run())
