"""渠道账号池服务：单 key 统计/启停、渠道连通性测试、模型自动发现。

key_meta 结构（存 Channel.key_meta JSON 文本）：
  {"<fp>": {"disabled": bool, "ok": int, "fail": int, "last_status": int, "last_ts": float}}
fp = key 指纹（sha256[:12]），与解密后的明文 key 对应，不存明文。
"""
from __future__ import annotations

import json
import time

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..adapters import get_adapter
from ..config import get_settings
from ..core.security import decrypt_secret, key_fingerprint
from ..db.base import get_sessionmaker
from ..db.models import Channel


class ChannelService:
    def __init__(self, crypto_secret: str | None = None):
        self._crypto_secret = crypto_secret

    def _secret(self) -> str:
        return self._crypto_secret or get_settings().crypto_secret

    def _decrypt_keys(self, ch: Channel) -> list[str]:
        secret = self._secret()
        return [decrypt_secret(k, secret) for k in json.loads(ch.api_keys or "[]")]

    def _meta(self, ch: Channel) -> dict:
        try:
            return json.loads(ch.key_meta or "{}")
        except Exception:
            return {}

    def key_summaries(self, ch: Channel) -> list[dict]:
        """返回每个 key 的脱敏摘要（指纹、掩码、启停、统计）。"""
        meta = self._meta(ch)
        out = []
        for k in self._decrypt_keys(ch):
            if not k:
                continue
            fp = key_fingerprint(k)
            m = meta.get(fp, {})
            masked = (k[:6] + "····" + k[-4:]) if len(k) > 12 else "····"
            out.append({
                "fp": fp, "masked": masked,
                "disabled": bool(m.get("disabled")),
                "ok": m.get("ok", 0), "fail": m.get("fail", 0),
                "last_status": m.get("last_status"), "last_ts": m.get("last_ts"),
            })
        return out

    async def record_key_result(self, channel_id: int, key_fp: str, ok: bool, status: int) -> None:
        """转发后按 key 指纹累计统计（独立 session，异步）。"""
        async with get_sessionmaker()() as session:
            ch = (await session.execute(select(Channel).where(Channel.id == channel_id))).scalar_one_or_none()
            if ch is None:
                return
            meta = self._meta(ch)
            m = meta.setdefault(key_fp, {"disabled": False, "ok": 0, "fail": 0})
            if ok:
                m["ok"] = m.get("ok", 0) + 1
            else:
                m["fail"] = m.get("fail", 0) + 1
            m["last_status"] = status
            m["last_ts"] = time.time()
            ch.key_meta = json.dumps(meta, ensure_ascii=False)
            await session.commit()

    async def set_key_disabled(self, session: AsyncSession, channel_id: int,
                               key_fp: str, disabled: bool) -> bool:
        ch = (await session.execute(select(Channel).where(Channel.id == channel_id))).scalar_one_or_none()
        if ch is None:
            return False
        meta = self._meta(ch)
        m = meta.setdefault(key_fp, {"disabled": False, "ok": 0, "fail": 0})
        m["disabled"] = disabled
        ch.key_meta = json.dumps(meta, ensure_ascii=False)
        await session.commit()
        return True

    def disabled_fingerprints(self, ch: Channel) -> set[str]:
        meta = self._meta(ch)
        return {fp for fp, m in meta.items() if m.get("disabled")}

    async def test(self, session: AsyncSession, channel_id: int, http: httpx.AsyncClient,
                   model: str | None = None, all_keys: bool = False) -> dict:
        """连通性测试：发一条极小 chat 请求，返回每个 key 的 ok/延迟/错误。不计费不记 usage。"""
        ch = (await session.execute(select(Channel).where(Channel.id == channel_id))).scalar_one_or_none()
        if ch is None:
            return {"error": "channel not found"}
        keys = [k for k in self._decrypt_keys(ch) if k]
        if not keys:
            return {"error": "no api keys configured"}
        models = json.loads(ch.models or "[]")
        test_model = model or next((m for m in models if m not in ("*",) and not m.endswith("*")), None)
        if not test_model:
            return {"error": "no concrete model to test; specify one"}
        upstream = json.loads(ch.model_map or "{}").get(test_model, test_model)
        headers_extra = json.loads(ch.headers or "{}")
        adapter = get_adapter(ch.type)
        payload = {"model": test_model, "messages": [{"role": "user", "content": "ping"}], "max_tokens": 1}

        targets = keys if all_keys else keys[:1]
        results = []
        for k in targets:
            url, headers, body = adapter.build_request(
                ch.base_url.rstrip("/"), upstream, k, payload, headers_extra, "chat")
            started = time.time()
            try:
                resp = await http.post(url, json=body, headers=headers, timeout=10.0)
                latency = int((time.time() - started) * 1000)
                ok = resp.status_code < 400
                err = None if ok else resp.text[:200]
                results.append({"fp": key_fingerprint(k), "masked": (k[:6] + "····" + k[-4:]),
                                "ok": ok, "status": resp.status_code, "latency_ms": latency, "error": err})
                await self.record_key_result(channel_id, key_fingerprint(k), ok, resp.status_code)
            except Exception as e:
                latency = int((time.time() - started) * 1000)
                results.append({"fp": key_fingerprint(k), "masked": (k[:6] + "····" + k[-4:]),
                                "ok": False, "status": 0, "latency_ms": latency, "error": str(e)[:200]})
                await self.record_key_result(channel_id, key_fingerprint(k), False, 0)
        return {"model": test_model, "results": results}

    async def discover_models(self, session: AsyncSession, channel_id: int,
                              http: httpx.AsyncClient) -> dict:
        """从上游 GET /models 拉取可用模型（仅 OpenAI 兼容）。"""
        ch = (await session.execute(select(Channel).where(Channel.id == channel_id))).scalar_one_or_none()
        if ch is None:
            return {"error": "channel not found"}
        if ch.type not in ("openai", "deepseek", "openrouter", "qwen"):
            return {"error": f"model discovery not supported for type '{ch.type}'; add models manually"}
        keys = [k for k in self._decrypt_keys(ch) if k]
        if not keys:
            return {"error": "no api keys"}
        url = ch.base_url.rstrip("/") + "/models"
        try:
            resp = await http.get(url, headers={"Authorization": f"Bearer {keys[0]}"}, timeout=10.0)
            if resp.status_code >= 400:
                return {"error": f"upstream {resp.status_code}: {resp.text[:200]}"}
            data = resp.json()
            ids = [m.get("id") for m in (data.get("data") or []) if m.get("id")]
            return {"models": sorted(ids)}
        except Exception as e:
            return {"error": str(e)[:200]}
