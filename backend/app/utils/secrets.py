"""配置密钥的加密封装（t162）

system_config 里的 ai_api_key / smtp_password 落库前加密，读取时解密；
历史明文值保持兼容（未带前缀原样返回），首次写入或迁移时自动封存。
"""
from __future__ import annotations

from app.utils.crypto import decrypt_value, encrypt_value

ENC_PREFIX = "enc:v1:"


def is_sealed(value) -> bool:
    return isinstance(value, str) and value.startswith(ENC_PREFIX)


def seal(value):
    if not value:
        return value
    if is_sealed(value):
        return value
    return ENC_PREFIX + encrypt_value(str(value))


def unseal(value):
    if not isinstance(value, str) or not value:
        return value
    if not is_sealed(value):
        return value
    try:
        return decrypt_value(value[len(ENC_PREFIX):])
    except Exception:  # noqa: BLE001
        return ""


def masked(value) -> bool:
    """前端回传的脱敏占位值（**** / •••• ）不覆盖已存密钥。"""
    if not isinstance(value, str):
        return False
    s = value.strip()
    if not s:
        return False
    return all(ch in "*•·." for ch in s) or (s.startswith("sk-") and s.endswith("****"))
