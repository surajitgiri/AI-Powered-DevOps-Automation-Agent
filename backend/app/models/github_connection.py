import uuid

from sqlalchemy import (
    Column,
    String,
    Boolean,
    DateTime,
    ForeignKey
)

from sqlalchemy.dialects.postgresql import UUID

from sqlalchemy.sql import func

from app.core.database import Base


class GitHubConnection(Base):

    __tablename__ = "github_connections"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )

    project_id = Column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False
    )

    github_username = Column(
        String(255),
        nullable=False
    )

    repository_url = Column(
        String(500),
        nullable=True
    )

    repository_name = Column(
        String(255),
        nullable=True
    )

    installation_id = Column(
        String(255),
        nullable=True
    )

    token_secret_ref = Column(
        String(500),
        nullable=False
    )

    is_active = Column(
        Boolean,
        default=True
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )