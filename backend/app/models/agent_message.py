import uuid

from sqlalchemy import (
    Column,
    String,
    Text,
    DateTime,
    ForeignKey,
    Integer
)

from sqlalchemy.dialects.postgresql import UUID, JSONB

from sqlalchemy.sql import func

from app.core.database import Base


class AgentMessage(Base):

    __tablename__ = "agent_messages"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("agent_sessions.id", ondelete="CASCADE"),
        nullable=False
    )

    role = Column(
        String(50),
        nullable=False
    )

    content = Column(
        Text,
        nullable=False
    )

    # "metadata" is reserved by SQLAlchemy's Declarative API.
    message_metadata = Column(
        "metadata",
        JSONB,
        nullable=True
    )

    token_usage = Column(
        Integer,
        nullable=True
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )