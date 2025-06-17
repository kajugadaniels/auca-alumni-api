import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator

class CreateEventSchema(BaseModel):
    event_date: datetime.date = Field(..., description="Date when the event takes place")
    description: str = Field(..., min_length=10, description="Event description")

    @field_validator("event_date")
    def date_not_in_past(cls, v: datetime.date) -> datetime.date:
        if v < datetime.date.today():
            raise ValueError("Event date cannot be in the past")
        return v

class UpcomingEventSchema(BaseModel):
    id: int
    photo: str
    date: datetime.date
    description: str
    status: str  # "Ended", "Happening", or "Upcoming"
    created_at: datetime.datetime
    updated_at: datetime.datetime

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
