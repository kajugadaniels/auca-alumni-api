from datetime import date
from pydantic import BaseModel, Field, HttpUrl, validator
from typing import Optional

class EventBase(BaseModel):
    photo: HttpUrl = Field(..., description="URL to the event image")
    date: date = Field(..., description="Date of the event (YYYY-MM-DD)")
    description: str = Field(..., min_length=10, max_length=1000, description="Detailed description")

    @validator("date")
    def date_not_in_past(cls, v: date):
        if v < date.today():
            raise ValueError("Event date cannot be in the past")
        return v

class EventCreate(EventBase):
    """Schema for creating a new event."""
    pass

class EventUpdate(BaseModel):
    """Schema for updating an existing event."""
    photo: Optional[HttpUrl] = None
    date: Optional[date] = None
    description: Optional[str] = Field(None, min_length=10, max_length=1000)

    @validator("date")
    def date_not_in_past(cls, v: date):
        if v and v < date.today():
            raise ValueError("Event date cannot be in the past")
        return v

class EventResponse(BaseModel):
    id: int
    photo: HttpUrl
    date: date
    description: str

    model_config = {"from_attributes": True}

class EventListResponse(BaseModel):
    status: str = "success"
    message: str
    data: list[EventResponse]

    model_config = {"from_attributes": True}
