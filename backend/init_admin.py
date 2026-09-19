# -*- coding: utf-8 -*-
"""Init admin account"""
from app.database import SessionLocal
from app.models.user import User, UserRole
from app.models.email_address import EmailAddress
from app.config import get_settings
from app.utils.security import hash_password
from datetime import datetime

settings = get_settings()

def init_admin():
    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.nickname == settings.admin_nickname).first()
        if existing:
            print(f"Admin already exists: {existing.nickname}, skipping")
            return

        admin = User(
            email=settings.admin_email,
            nickname=settings.admin_nickname,
            password_hash=hash_password(settings.admin_init_password),
            role=UserRole.ADMIN,
            force_change_password=False,   # 已取消首次强制改密机制
        )
        db.add(admin)
        db.flush()

        primary_email = EmailAddress(
            user_id=admin.id,
            email=admin.email,
            is_primary=True,
            is_verified=True,
            verified_at=datetime.utcnow(),
        )
        db.add(primary_email)
        db.commit()

        print("Admin created successfully!")
        print(f"   Nickname: {admin.nickname}")
        print(f"   Email: {admin.email}")
        print("   Please change password on first login")
    finally:
        db.close()

if __name__ == "__main__":
    init_admin()
