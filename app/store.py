"""数据层：管理访问令牌(tokens) + 请求用量(requests)，SQLite 存储。"""
import secrets
import sqlite3
import threading
import time

# tokens 表的完整列（用于新建 + 旧库迁移补列）
_TOKEN_COLUMNS = {
    "key": "TEXT UNIQUE",
    "name": "TEXT",
    "enabled": "INTEGER DEFAULT 1",
    "quota_tokens": "INTEGER",
    "used_tokens": "INTEGER DEFAULT 0",
    "created_at": "REAL",
    "note": "TEXT",
    "expires_at": "REAL",
    "rpm_limit": "INTEGER",
    "allowed_models": "TEXT",
}

_UPDATABLE = {"name", "note", "enabled", "quota_tokens", "expires_at", "rpm_limit", "allowed_models"}

# requests 表里后加的列（旧库迁移补列）
_REQUEST_COLUMNS = {"token_id": "INTEGER", "token_name": "TEXT"}


def new_key() -> str:
    return "sk-" + secrets.token_urlsafe(24)


class Database:
    def __init__(self, db_path: str = "usage.db"):
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init()

    def _init(self):
        c = self._conn
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts REAL, model TEXT, upstream_model TEXT, channel TEXT,
                status INTEGER, latency_ms INTEGER,
                prompt_tokens INTEGER, completion_tokens INTEGER, total_tokens INTEGER,
                stream INTEGER, token_id INTEGER, token_name TEXT, error TEXT
            )
            """
        )
        cols = ", ".join(f"{n} {t}" for n, t in _TOKEN_COLUMNS.items())
        c.execute(f"CREATE TABLE IF NOT EXISTS tokens (id INTEGER PRIMARY KEY AUTOINCREMENT, {cols})")
        self._migrate()
        c.commit()

    def _migrate(self):
        """旧库补齐缺失的列。"""
        self._ensure_columns("tokens", _TOKEN_COLUMNS)
        self._ensure_columns("requests", _REQUEST_COLUMNS)

    def _ensure_columns(self, table, columns):
        existing = {r["name"] for r in self._conn.execute(f"PRAGMA table_info({table})").fetchall()}
        for name, decl in columns.items():
            if name not in existing:
                # 加列时不能带 UNIQUE 约束，去掉
                self._conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {decl.replace('UNIQUE', '')}")

    # ---------------- tokens ----------------
    def create_token(self, name, quota_tokens=None, note=None,
                     expires_at=None, rpm_limit=None, allowed_models=None, key=None) -> dict:
        key = key or new_key()
        with self._lock:
            cur = self._conn.execute(
                "INSERT INTO tokens (key,name,enabled,quota_tokens,used_tokens,created_at,note,"
                "expires_at,rpm_limit,allowed_models) VALUES (?,?,1,?,0,?,?,?,?,?)",
                (key, name, quota_tokens, time.time(), note, expires_at, rpm_limit, allowed_models),
            )
            self._conn.commit()
            tid = cur.lastrowid
        return self.get_token_by_id(tid)

    def get_token_by_key(self, key) -> dict | None:
        row = self._conn.execute("SELECT * FROM tokens WHERE key=?", (key,)).fetchone()
        return dict(row) if row else None

    def get_token_by_id(self, tid) -> dict | None:
        row = self._conn.execute("SELECT * FROM tokens WHERE id=?", (tid,)).fetchone()
        return dict(row) if row else None

    def list_tokens(self) -> list:
        rows = self._conn.execute("SELECT * FROM tokens ORDER BY id").fetchall()
        return [dict(r) for r in rows]

    def update_token(self, tid, **fields):
        cols = {k: v for k, v in fields.items() if k in _UPDATABLE}
        if not cols:
            return self.get_token_by_id(tid)
        if "enabled" in cols:
            cols["enabled"] = 1 if cols["enabled"] else 0
        sets = ", ".join(f"{k}=?" for k in cols)
        with self._lock:
            self._conn.execute(f"UPDATE tokens SET {sets} WHERE id=?", (*cols.values(), tid))
            self._conn.commit()
        return self.get_token_by_id(tid)

    # 兼容旧调用
    def set_enabled(self, tid, enabled: bool):
        self.update_token(tid, enabled=enabled)

    def update_quota(self, tid, quota_tokens):
        self.update_token(tid, quota_tokens=quota_tokens)

    def delete_token(self, tid):
        with self._lock:
            self._conn.execute("DELETE FROM tokens WHERE id=?", (tid,))
            self._conn.commit()

    def add_usage(self, tid, tokens):
        if not tid or not tokens:
            return
        with self._lock:
            self._conn.execute("UPDATE tokens SET used_tokens=used_tokens+? WHERE id=?", (tokens, tid))
            self._conn.commit()

    # ---------------- requests ----------------
    def log(self, **kw):
        with self._lock:
            self._conn.execute(
                """INSERT INTO requests
                   (ts, model, upstream_model, channel, status, latency_ms,
                    prompt_tokens, completion_tokens, total_tokens, stream,
                    token_id, token_name, error)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    kw.get("ts", time.time()), kw.get("model"), kw.get("upstream_model"),
                    kw.get("channel"), kw.get("status"), kw.get("latency_ms"),
                    kw.get("prompt_tokens"), kw.get("completion_tokens"), kw.get("total_tokens"),
                    1 if kw.get("stream") else 0, kw.get("token_id"), kw.get("token_name"),
                    kw.get("error"),
                ),
            )
            self._conn.commit()

    def recent(self, limit: int = 100) -> list:
        cur = self._conn.execute(
            "SELECT ts, model, channel, status, latency_ms, total_tokens, stream, token_name "
            "FROM requests ORDER BY id DESC LIMIT ?",
            (limit,),
        )
        return [dict(r) for r in cur.fetchall()]

    def summary_by_channel(self) -> list:
        cur = self._conn.execute(
            "SELECT channel, COUNT(*) AS requests, COALESCE(SUM(total_tokens),0) AS tokens, "
            "ROUND(AVG(latency_ms)) AS avg_latency_ms FROM requests GROUP BY channel"
        )
        return [dict(r) for r in cur.fetchall()]

    def summary_by_token(self) -> list:
        cur = self._conn.execute(
            "SELECT COALESCE(token_name,'(unknown)') AS token_name, COUNT(*) AS requests, "
            "COALESCE(SUM(total_tokens),0) AS tokens FROM requests GROUP BY token_name ORDER BY tokens DESC"
        )
        return [dict(r) for r in cur.fetchall()]
