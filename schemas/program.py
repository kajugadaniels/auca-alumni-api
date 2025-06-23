import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, validator

# ----------------------------------------
# Schema for creating a Program
# ----------------------------------------
class CreateProgramSchema(BaseModel):
    title: str = Field(..., min_length=5, description="Program title (min 5 characters)")
    description: str = Field(..., min_length=10, description="Program description (min 10 characters)")

    @validator("title")
    def title_must_not_be_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Title must not be blank")
        return v.strip()

    @validator("description")
    def description_must_not_be_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Description must not be blank")
        return v.strip()


# ----------------------------------------
# Response schema for a single Program
# ----------------------------------------
class ProgramSchema(BaseModel):
    id: int
    title: str
    description: str
    photo: str               # fully qualified URL
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = {
        "from_attributes": True
    }


# ----------------------------------------
# Paginated list response for Programs
# ----------------------------------------
class ProgramListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    next_page: Optional[str]
    prev_page: Optional[str]
    items: List[ProgramSchema]

    model_config = {
        "from_attributes": True
    }
