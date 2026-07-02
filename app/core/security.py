"""安全工具：令牌生成、密码哈希、上游 key 的对称加密存储。"""
import base64
import hashlib
import secrets

from cryptography.fernet import Fernet, InvalidToken
from passlib.context import CryptContext

_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")


def new_token_key() -> str:
    return "sk-" + secrets.token_urlsafe(24)


def hash_password(password: str) -> str:
    return _pwd.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    try:
        return _pwd.verify(password, hashed)
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
