import enum

from sqlalchemy import JSON, Boolean, Column, DateTime, Enum, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID

from core.db.base import Base


class RepoStatus(enum.Enum):
    active = "active"
    inactive = "inactive"
    error = "error"
    syncing = "syncing"


class SyncStatus(enum.Enum):
    pending = "pending"
    in_progress = "progress"
    success = "success"
    failed = "failed"
    skipped = "skipped"


class Repository(Base):
    __tablename__ = "repositories"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    name = Column(String(255), nullable=False)
    status = Column(
        Enum(RepoStatus, native_enum=True, name="repo_status"), nullable=False, server_default=RepoStatus.active.value
    )
    provider = Column(String(255), nullable=False, index=True)
    api_url = Column(String(1024), nullable=False)
    clone_url = Column(String(1024), nullable=False)
    description = Column(Text)

    branch = Column(String(255), nullable=False, server_default="main")
    active = Column(Boolean, nullable=False, server_default="true")
    auto_sync = Column(Boolean, nullable=False, server_default="true")
    enable_polling = Column(Boolean, nullable=False, server_default="true")
    enable_webhooks = Column(Boolean, nullable=False, server_default="false")

    sync_interval = Column(Integer, nullable=False, server_default="3000")
    max_retries = Column(Integer, nullable=False, server_default="3")
    retry_delay = Column(Integer, nullable=False, server_default="1000")

    last_sync_status = Column(
        Enum(SyncStatus, native_enum=True, name="sync_status"), nullable=False, server_default=SyncStatus.pending.value
    )
    last_successful_sync_at = Column(DateTime(timezone=True))
    last_sync_at = Column(DateTime(timezone=True))

    last_commit_hash = Column(String(128))
    last_commit_message = Column(Text)
    last_commit_author = Column(String(255))
    last_commit_timestamp = Column(DateTime(timezone=True))

    sync_count = Column(Integer, nullable=False, server_default="0")
    failed_sync_count = Column(Integer, nullable=False, server_default="0")
    total_commits_synced = Column(Integer, nullable=False, server_default="0")

    meta = Column(JSON, nullable=False, server_default="{}")

    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True))

    def __repr__(self):
        return f"<Repository {self.provider} ({self.status})>"
