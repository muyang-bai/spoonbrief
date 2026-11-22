from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String

from app.database import Base


class AilifeosLink(Base):
    """一勺热点用户 <-> AiLifeOS 账号 关联（由 AiLifeOS 通过 profile/sync 写入）"""

    __tablename__ = "ailifeos_links"

    user_id = Column(Integer, primary_key=True)
    ailifeos_uid = Column(String(64), nullable=True, index=True)
    tier = Column(String(24), nullable=True)
    sync_enabled = Column(Boolean, default=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
