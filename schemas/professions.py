import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, validator

# ----------------------------------------
# Schema for creating/updating a Profession
# ----------------------------------------
class CreateProfessionSchema(BaseModel):
    name: str = Field(..., min_length=2, description="Profession name (min 2 characters)")

    @validator("name")
    def name_not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Profession name must not be blank")
        return v

# ----------------------------------------
# Schema for returning a single Profession
# ----------------------------------------
class ProfessionSchema(BaseModel):
    id: int
    name: str
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = {"from_attributes": True}

# ----------------------------------------
# Schema for paginated list of Professions
# ----------------------------------------
class ProfessionListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    next_page: Optional[str]
    prev_page: Optional[str]
    items: List[ProfessionSchema]

    model_config = {"from_attributes": True}
