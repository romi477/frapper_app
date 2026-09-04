from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class TextEnCreate(BaseModel):
    title: str = Field(min_length=1)
    body: str = Field(min_length=1)
    tags: str = ''


class TextEnUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1)
    body: Optional[str] = Field(default=None, min_length=1)
    tags: Optional[str] = None


class TextEnSummary(BaseModel):
    id: int
    title: str
    tags: str
    created_at: datetime


class TextEnResponse(BaseModel):
    id: int
    title: str
    body: str
    tags: str
    created_at: datetime
    updated_at: datetime
