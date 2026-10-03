from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    ForeignKey,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(255), unique=True)
    password_hash: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    projects: Mapped[list["Project"]] = relationship(
        back_populates="owner", cascade="all, delete-orphan"
    )
    sessions: Mapped[list["UserSession"]] = relationship(
        cascade="all, delete-orphan"
    )


class UserSession(Base):
    __tablename__ = "user_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column()


class Project(Base):
    __tablename__ = "projects"
    __table_args__ = (
        UniqueConstraint("owner_id", "name"),
        CheckConstraint("status IN ('draft', 'active', 'archived')"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(160))
    description: Mapped[str | None] = mapped_column(Text)
    location: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(20), server_default="draft")
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )

    owner: Mapped[User] = relationship(back_populates="projects")
    terrains: Mapped[list["Terrain"]] = relationship(cascade="all, delete-orphan")
    files: Mapped[list["File"]] = relationship(cascade="all, delete-orphan")
    plans: Mapped[list["Plan"]] = relationship(cascade="all, delete-orphan")
    elevations: Mapped[list["Elevation"]] = relationship(cascade="all, delete-orphan")
    materials: Mapped[list["Material"]] = relationship(cascade="all, delete-orphan")
    recommendations: Mapped[list["Recommendation"]] = relationship(
        cascade="all, delete-orphan"
    )
    conversations: Mapped[list["AIConversation"]] = relationship(
        cascade="all, delete-orphan"
    )


class Terrain(Base):
    __tablename__ = "terrains"
    __table_args__ = (
        CheckConstraint("area_m2 > 0"),
        CheckConstraint("width_m > 0"),
        CheckConstraint("length_m > 0"),
        CheckConstraint("slope_percent >= 0"),
        CheckConstraint("latitude BETWEEN -90 AND 90"),
        CheckConstraint("longitude BETWEEN -180 AND 180"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(160))
    area_m2: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    width_m: Mapped[Decimal | None] = mapped_column(Numeric(8, 2))
    length_m: Mapped[Decimal | None] = mapped_column(Numeric(8, 2))
    slope_percent: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    soil_type: Mapped[str | None] = mapped_column(String(80))
    latitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    longitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class File(Base):
    __tablename__ = "files"
    __table_args__ = (CheckConstraint("size_bytes >= 0"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    uploaded_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    filename: Mapped[str] = mapped_column(String(255))
    storage_path: Mapped[str] = mapped_column(String(500))
    mime_type: Mapped[str] = mapped_column(String(120))
    size_bytes: Mapped[int] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class Plan(Base):
    __tablename__ = "plans"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    file_id: Mapped[int | None] = mapped_column(
        ForeignKey("files.id", ondelete="SET NULL")
    )
    title: Mapped[str] = mapped_column(String(160))
    level: Mapped[str | None] = mapped_column(String(60))
    scale: Mapped[str | None] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class Elevation(Base):
    __tablename__ = "elevations"
    __table_args__ = (
        CheckConstraint("orientation IN ('north', 'south', 'east', 'west')"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    file_id: Mapped[int | None] = mapped_column(
        ForeignKey("files.id", ondelete="SET NULL")
    )
    title: Mapped[str] = mapped_column(String(160))
    orientation: Mapped[str] = mapped_column(String(10))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class Material(Base):
    __tablename__ = "materials"
    __table_args__ = (
        UniqueConstraint("project_id", "name"),
        CheckConstraint("quantity >= 0"),
        CheckConstraint("unit_cost >= 0"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(160))
    category: Mapped[str | None] = mapped_column(String(80))
    unit: Mapped[str] = mapped_column(String(20))
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 2), server_default="0")
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(12, 2), server_default="0")
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class Recommendation(Base):
    __tablename__ = "recommendations"
    __table_args__ = (CheckConstraint("source IN ('ai', 'user', 'system')"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    category: Mapped[str] = mapped_column(String(80))
    content: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(10), server_default="ai")
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class AIConversation(Base):
    __tablename__ = "ai_conversations"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    title: Mapped[str | None] = mapped_column(String(160))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    messages: Mapped[list["AIMessage"]] = relationship(
        cascade="all, delete-orphan", order_by="AIMessage.id"
    )


class AIMessage(Base):
    __tablename__ = "ai_messages"
    __table_args__ = (CheckConstraint("role IN ('user', 'assistant', 'system')"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    conversation_id: Mapped[int] = mapped_column(
        ForeignKey("ai_conversations.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[str] = mapped_column(String(10))
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
