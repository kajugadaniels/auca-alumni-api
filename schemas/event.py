from datetime import date
from typing import List, Optional
from pydantic import BaseModel, Field, HttpUrl, validator

class CreateEventSchema(BaseModel):
    photo: HttpUrl = Field(..., description="URL to the event photo")
    date: date = Field(..., description="Date when the event takes place")
    description: str = Field(..., min_length=10, description="Event description")

    @validator("date")
    def date_not_in_past(cls, v):
        if v < date.today():
            raise ValueError("Event date cannot be in the past")
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
