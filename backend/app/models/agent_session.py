import uuid

from sqlalchemy import (
    Column,
    String,
    DateTime,
    ForeignKey
)

from sqlalchemy.dialects.postgresql import UUID

from sqlalchemy.sql import func

from app.core.database import Base


class AgentSession(Base):

    __tablename__ = "agent_sessions"

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
        ForeignKey("projects.id", ondelete="SET NULL"),
        nullable=True
    )

    title = Column(
        String(255),
        nullable=True
    )

    agent_type = Column(
        String(100),
        default="deployment"
    )

    status = Column(
        String(50),
        default="active"
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