import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, validator

# ----------------------------------------
# Schema for creating a Social Activity
# ----------------------------------------
class CreateSocialActivitySchema(BaseModel):
    title: str = Field(..., min_length=5, description="Activity title (min 5 characters)")
    description: str = Field(..., min_length=10, description="Activity description (min 10 characters)")
    date: datetime.date = Field(..., description="Date of the activity")

    @validator("title")
    def title_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Title must not be blank")
        return v.strip()

    @validator("description")
    def description_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Description must not be blank")
        return v.strip()

    @validator("date")
    def date_not_in_past(cls, v: datetime.date) -> datetime.date:
        # Allow past activities if desired; otherwise enforce v >= today()
        return v

class SocialActivitySchema(BaseModel):
    id: int
    photo: str
    title: str
    description: str
    date: datetime.date
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = {
        "from_attributes": True
    }

class SocialActivityListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    next_page: Optional[str]
    prev_page: Optional[str]
    items: List[SocialActivitySchema]

    model_config = {
        "from_attributes": True
    }
