"""安全工具：令牌生成、密码哈希、上游 key 的对称加密存储。"""
import base64
import hashlib
import secrets

import bcrypt
from cryptography.fernet import Fernet, InvalidToken


def new_token_key() -> str:
    return "sk-" + secrets.token_urlsafe(24)


def key_fingerprint(plaintext_key: str) -> str:
    """key 的短指纹（sha256 前 12 位），用于统计索引，不泄露明文。"""
    return hashlib.sha256(plaintext_key.encode("utf-8")).hexdigest()[:12]


def _prehash(password: str) -> bytes:
    """bcrypt 只取前 72 字节。先做 sha256 再 base64，规避长度上限且不丢熵。"""
    digest = hashlib.sha256(password.encode("utf-8")).digest()
    return base64.b64encode(digest)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(_prehash(password), bcrypt.gensalt()).decode("ascii")


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(_prehash(password), hashed.encode("ascii"))
    except Exception:
        return False


def _fernet(secret: str) -> Fernet:
    # 从任意长度 secret 派生 32 字节 key
    digest = hashlib.sha256(secret.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_secret(plaintext: str, secret: str) -> str:
    return _fernet(secret).encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt_secret(ciphertext: str, secret: str) -> str:
    try:
        return _fernet(secret).decrypt(ciphertext.encode("utf-8")).decode("utf-8")
    except (InvalidToken, ValueError):
        # 兼容明文（迁移期）或损坏数据
        return ciphertext
