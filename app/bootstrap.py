"""启动初始化：建表、创建默认 admin 用户、从旧 config.yaml 导入渠道（仅首次）。"""
import json
import os

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from .config import Settings
from .core.security import encrypt_secret
from .db.base import create_all, get_sessionmaker
from .db.models import Channel, User


async def bootstrap(settings: Settings) -> None:
    await create_all()
    async with get_sessionmaker()() as session:
        await _ensure_admin_user(session)
        await _import_legacy_channels(session, settings)


async def _ensure_admin_user(session: AsyncSession) -> None:
    count = (await session.execute(select(func.count()).select_from(User))).scalar_one()
    if count == 0:
        session.add(User(username="admin", role="admin", group="default", balance=0))
        await session.commit()


async def _import_legacy_channels(session: AsyncSession, settings: Settings) -> None:
    """若 channels 表为空且存在旧 config.yaml，导入其渠道定义（含环境变量插值后的 key）。"""
    count = (await session.execute(select(func.count()).select_from(Channel))).scalar_one()
    if count > 0:
        return
    path = settings.legacy_config_path
    if not path or not os.path.exists(path):
        return
    try:
        import re
        import yaml

        with open(path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}
    except Exception:
        return

    env_pat = re.compile(r"\$\{([^}]+)\}")

    def interp(v):
        if isinstance(v, str):
            return env_pat.sub(lambda m: os.environ.get(m.group(1), ""), v)
        if isinstance(v, list):
            return [interp(x) for x in v]
        if isinstance(v, dict):
            return {k: interp(x) for k, x in v.items()}
        return v

    raw = interp(raw)
    secret = settings.crypto_secret
    imported = 0
    for ch in raw.get("channels") or []:
        keys = [str(k).strip() for k in (ch.get("api_keys") or []) if k and str(k).strip()]
        if not keys:
            continue
        enc = [encrypt_secret(k, secret) for k in keys]
        session.add(Channel(
            name=ch.get("name") or "channel", type=ch.get("type") or "openai",
            base_url=(ch.get("base_url") or "").rstrip("/"),
            api_keys=json.dumps(enc), models=json.dumps(ch.get("models") or []),
            model_map=json.dumps(ch.get("model_map") or {}),
            headers=json.dumps(ch.get("headers") or {}),
        ))
        imported += 1
    if imported:
        await session.commit()
        print(f"✅ 从 {path} 导入了 {imported} 个渠道")
