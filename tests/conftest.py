import socket
import threading
import time

import httpx
import pytest
import uvicorn
from fastapi.testclient import TestClient

from app.main import create_app
from tests.mock_upstream import build_mock_app


def _free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


class _Server(uvicorn.Server):
    def install_signal_handlers(self):  # 在线程里运行，禁用信号处理
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
            if httpx.get(base + "/healthz", timeout=0.5).status_code == 200:
                break
        except Exception:
            time.sleep(0.05)
    else:
        raise RuntimeError("mock upstream failed to start")

    yield base + "/v1"
    server.should_exit = True
    thread.join(timeout=5)


@pytest.fixture
def gateway(mock_upstream):
    config = {
        "server": {"host": "127.0.0.1", "port": 0},
        "auth": {"client_keys": ["TESTKEY"], "admin_key": "ADMINKEY"},
        "logging": {"db_path": ":memory:"},
        "channels": [
            {"name": "mock-deepseek", "base_url": mock_upstream, "api_keys": ["GOOD_KEY"],
             "models": ["deepseek-chat"], "model_map": {}, "headers": {}},
            {"name": "mock-fallback", "base_url": mock_upstream, "api_keys": ["BAD_KEY", "GOOD_KEY"],
             "models": ["fallback-model"], "model_map": {}, "headers": {}},
            {"name": "mock-catchall", "base_url": mock_upstream, "api_keys": ["GOOD_KEY"],
             "models": ["*"], "model_map": {"claude": "anthropic/claude-x"}, "headers": {}},
        ],
    }
    with TestClient(create_app(config)) as client:
        yield client
