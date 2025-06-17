from datetime import date
from typing import List, Optional
from pydantic import BaseModel, Field, validator

class UpcomingEventCreateSchema(BaseModel):
    photo: str = Field(..., description="URL or path to the event photo")
    date: date = Field(..., description="Date of the event")
    description: str = Field(..., description="Event description")

    @validator("photo", "description")
    def not_empty(cls, v, field):
        if not v.strip():
            raise ValueError(f"{field.name} cannot be empty")
        return v

class UpcomingEventSchema(BaseModel):
    id: int
    photo: str
    date: date
    description: str
    status: str  # "Ended", "Happening", or "Upcoming"

    model_config = {
        "from_attributes": True
    }

class UpcomingEventListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    next_page: Optional[str]
    prev_page: Optional[str]
    items: List[UpcomingEventSchema]

    model_config = {
        "from_attributes": True
    }
