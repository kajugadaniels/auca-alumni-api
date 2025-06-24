import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, validator

# ----------------------------------------
# Schema for creating/updating a Faculty
# ----------------------------------------
class CreateFacultySchema(BaseModel):
    name: str = Field(..., min_length=3, description="Faculty name (min 3 characters)")
    description: str = Field(..., min_length=10, description="Faculty description (min 10 characters)")

    @validator("name")
    def name_not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Name must not be blank")
        return v

    @validator("description")
    def description_not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Description must not be blank")
        return v

# ----------------------------------------
# Schema for returning a single Faculty
# ----------------------------------------
class FacultySchema(BaseModel):
    id: int
    name: str
    description: str
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = {"from_attributes": True}

# ----------------------------------------
# Schema for paginated list of Faculties
# ----------------------------------------
class FacultyListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    next_page: Optional[str]
    prev_page: Optional[str]
    items: List[FacultySchema]

    model_config = {"from_attributes": True}
