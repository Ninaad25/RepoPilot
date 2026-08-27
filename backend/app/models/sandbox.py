from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String

from app.database import Base


class Sandbox(Base):
    __tablename__ = "sandboxes"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    sandbox_id = Column(
        String,
        unique=True,
        index=True,
        nullable=False,
    )

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )

    repo_url = Column(
        String,
        nullable=False,
    )

    container_id = Column(
        String,
        nullable=True,
    )

    container_name = Column(
        String,
        nullable=True,
    )

    image_name = Column(
        String,
        nullable=True,
    )

    workspace = Column(
        String,
        nullable=True,
    )

    host_port = Column(
        Integer,
        nullable=True,
    )

    container_port = Column(
        Integer,
        nullable=True,
    )

    status = Column(
        String,
        nullable=False,
        default="BUILDING",
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )