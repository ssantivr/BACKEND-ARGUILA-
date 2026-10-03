from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ProjectStatus = Literal["draft", "active", "archived"]


class UserCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: str = Field(max_length=255, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str
    created_at: datetime


class ProjectCreate(BaseModel):
    owner_id: int
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
    slope_percent: float | None = Field(default=None, ge=0, lt=1000)
    soil_type: str | None = Field(default=None, max_length=80)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)


class TerrainUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    area_m2: float | None = Field(default=None, gt=0, lt=1e10)
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
