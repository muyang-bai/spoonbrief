"""
API Key 对称加密存储
"""

from __future__ import annotations
import base64

from cryptography.fernet import Fernet

from app.config import get_settings

settings = get_settings()

def _get_fernet() -> Fernet:
    key = settings.encryption_key
    if not key:
        raise ValueError("ENCRYPTION_KEY 未配置")
    # 确保 key 是 base64 编码的 32 字节
    if len(key) < 44:
        key = base64.urlsafe_b64encode(key.ljust(32).encode()[:32])
    return Fernet(key.encode() if isinstance(key, str) else key)

def encrypt_value(plaintext: str) -> str:
    f = _get_fernet()
    return f.encrypt(plaintext.encode()).decode()

def decrypt_value(ciphertext: str) -> str:
    f = _get_fernet()
    return f.decrypt(ciphertext.encode()).decode()