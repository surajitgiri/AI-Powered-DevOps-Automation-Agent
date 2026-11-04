import uuid

from sqlalchemy import (
    Column,
    String,
    Text,
    DateTime,
    ForeignKey
)

from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.core.database import Base
# Ensure User model is loaded into Base.metadata for foreign key resolution
from app.models.user import User

class Project(Base):
    __tablename__ = "projects"

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

    name = Column(
        String(150),
        nullable=False
    )

    description = Column(Text)

    repository_url = Column(Text)

    repository_name = Column(String(255))

    default_branch = Column(
        String(100),
        default="main"
    )

    project_type = Column(String(50))

    deployment_platform = Column(String(50))

    status = Column(
        String(30),
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
