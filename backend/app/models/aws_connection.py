import uuid

from sqlalchemy import (
    Column,
    String,
    Text,
    Boolean,
    DateTime,
    ForeignKey
)

from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.core.database import Base


class AWSConnection(Base):

    __tablename__ = "aws_connections"

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

    account_id = Column(
        String(50),
        nullable=True
    )

    region = Column(
        String(50),
        nullable=False,
        default="ap-south-1"
    )

    role_arn = Column(
        Text,
        nullable=True
    )

    external_id_secret_ref = Column(
        Text,
        nullable=True
    )

    ecr_repository = Column(
        String(255),
        nullable=True
    )

    ec2_instance_id = Column(
        String(100),
        nullable=True
    )

    ssm_enabled = Column(
        Boolean,
        default=False
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
