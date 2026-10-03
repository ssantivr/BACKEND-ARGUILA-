from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ProjectStatus = Literal["draft", "active", "archived"]
Orientation = Literal["north", "south", "east", "west"]
RecommendationSource = Literal["ai", "user", "system"]


class RegisterRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: str = Field(max_length=255, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: str = Field(max_length=255)
    password: str = Field(max_length=128)


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str
    created_at: datetime


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    description: str | None = None
    location: str | None = Field(default=None, max_length=255)
    status: ProjectStatus = "draft"


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    description: str | None = None
    location: str | None = Field(default=None, max_length=255)
    status: ProjectStatus | None = None


class ProjectRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    owner_id: int
    name: str
    description: str | None
    location: str | None
    status: ProjectStatus
    created_at: datetime
    updated_at: datetime


class TerrainCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    area_m2: float = Field(gt=0, lt=1e10)
    width_m: float | None = Field(default=None, gt=0, lt=1e6)
    length_m: float | None = Field(default=None, gt=0, lt=1e6)
    slope_percent: float | None = Field(default=None, ge=0, lt=1000)
    soil_type: str | None = Field(default=None, max_length=80)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)


class TerrainUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    area_m2: float | None = Field(default=None, gt=0, lt=1e10)
    width_m: float | None = Field(default=None, gt=0, lt=1e6)
    length_m: float | None = Field(default=None, gt=0, lt=1e6)
    slope_percent: float | None = Field(default=None, ge=0, lt=1000)
    soil_type: str | None = Field(default=None, max_length=80)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)


class TerrainRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    name: str
    area_m2: float
    width_m: float | None
    length_m: float | None
    slope_percent: float | None
    soil_type: str | None
    latitude: float | None
    longitude: float | None
    created_at: datetime


class MaterialCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    category: str | None = Field(default=None, max_length=80)
    unit: str = Field(min_length=1, max_length=20)
    quantity: float = Field(default=0, ge=0, lt=1e10)
    unit_cost: float = Field(default=0, ge=0, lt=1e10)


class MaterialUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    category: str | None = Field(default=None, max_length=80)
    unit: str | None = Field(default=None, min_length=1, max_length=20)
    quantity: float | None = Field(default=None, ge=0, lt=1e10)
    unit_cost: float | None = Field(default=None, ge=0, lt=1e10)


class MaterialRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    name: str
    category: str | None
    unit: str
    quantity: float
    unit_cost: float
    created_at: datetime


class PlanCreate(BaseModel):
    file_id: int | None = None
    title: str = Field(min_length=1, max_length=160)
    level: str | None = Field(default=None, max_length=60)
    scale: str | None = Field(default=None, max_length=20)


class PlanUpdate(BaseModel):
    file_id: int | None = None
    title: str | None = Field(default=None, min_length=1, max_length=160)
    level: str | None = Field(default=None, max_length=60)
    scale: str | None = Field(default=None, max_length=20)


class PlanRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    file_id: int | None
    title: str
    level: str | None
    scale: str | None
    created_at: datetime


class ElevationCreate(BaseModel):
    file_id: int | None = None
    title: str = Field(min_length=1, max_length=160)
    orientation: Orientation


class ElevationUpdate(BaseModel):
    file_id: int | None = None
    title: str | None = Field(default=None, min_length=1, max_length=160)
    orientation: Orientation | None = None


class ElevationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    file_id: int | None
    title: str
    orientation: Orientation
    created_at: datetime


class DeletedItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    kind: Literal["terrain", "material", "plan", "elevation"]
    label: str


class RecommendationCreate(BaseModel):
    category: str = Field(min_length=1, max_length=80)
    content: str = Field(min_length=1, max_length=2000)


class RecommendationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    category: str
    content: str
    source: RecommendationSource
    created_at: datetime


class FileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    filename: str
    mime_type: str
    size_bytes: int
    created_at: datetime


class ConversationCreate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=160)


class ConversationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    title: str | None
    created_at: datetime


class MessageCreate(BaseModel):
    content: str = Field(min_length=1, max_length=4000)


class MessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    conversation_id: int
    role: Literal["user", "assistant", "system"]
    content: str
    created_at: datetime


class ConversationDetail(ConversationRead):
    messages: list[MessageRead]


class SummaryRead(BaseModel):
    projects: int
    draft_projects: int
    active_projects: int
    archived_projects: int
    terrains: int
    total_area_m2: float
    materials_total_cost: float
