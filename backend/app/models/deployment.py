import uuid

from sqlalchemy import (
    Column,
    String,
    Text,
    DateTime,
    ForeignKey
)

from sqlalchemy.dialects.postgresql import UUID, JSONB

from sqlalchemy.sql import func

from app.core.database import Base


class Deployment(Base):

    __tablename__ = "deployments"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    project_id = Column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False
    )

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )

    aws_connection_id = Column(
        UUID(as_uuid=True),
        ForeignKey("aws_connections.id", ondelete="SET NULL"),
        nullable=True
    )

    session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("agent_sessions.id", ondelete="SET NULL"),
        nullable=True
    )

    environment = Column(
        String(50),
        nullable=False
    )

    repository_url = Column(
        String(500),
        nullable=True
    )

    branch = Column(
        String(255),
        nullable=True
    )

    commit_sha = Column(
        String(100),
        nullable=True
    )

    docker_image = Column(
        String(500),
        nullable=True
    )

    image_digest = Column(
        String(255),
        nullable=True
    )

    previous_image = Column(
        String(500),
        nullable=True
    )

    status = Column(
        String(50),
        default="planned"
    )

    deployment_plan = Column(
        JSONB,
        nullable=True
    )

    error_message = Column(
        Text,
        nullable=True
    )

    started_at = Column(
        DateTime(timezone=True),
        nullable=True
    )

    completed_at = Column(
        DateTime(timezone=True),
        nullable=True
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )