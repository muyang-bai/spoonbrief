from __future__ import annotations
from pydantic import BaseModel, EmailStr, field_validator
from app.models.user import User

class SendCodeRequest(BaseModel):
    email: EmailStr

class RegisterRequest(BaseModel):
    email: EmailStr
    code: str          # 邮箱验证码
    nickname: str
    password: str

    @field_validator("nickname")
    @classmethod
    def validate_nickname(cls, v):
        if not User.validate_nickname(v):
            raise ValueError("昵称需 2-20 位，仅允许字母、连字符、中文")
        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v):
        if not User.validate_password(v):
            raise ValueError("密码需 8-72 字节且同时包含字母与数字")
        return v

class LoginRequest(BaseModel):
    account: str       # 邮箱或昵称
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserInfo"

class UserInfo(BaseModel):
    id: int
    email: str
    nickname: str
    role: str
    force_change_password: bool

    class Config:
        from_attributes = True

TokenResponse.model_rebuild()