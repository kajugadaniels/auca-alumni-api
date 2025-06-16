from pydantic import BaseModel, Field, validator
from datetime import date as DateType
from typing import Optional

class EventBase(BaseModel):
    photo: str = Field(..., max_length=255, description="URL to event photo")
    date: DateType = Field(..., description="Date of the event")   # now uses DateType
    description: str = Field(..., description="Detailed description")

    @validator("photo")
    def must_be_valid_url(cls, v):
        if not (v.startswith("http://") or v.startswith("https://")):
            raise ValueError("Photo must be a valid URL")
        return v

class EventCreate(EventBase):
    """Fields required to create a new event."""
    pass  # inherits all validators

class EventUpdate(BaseModel):
    """Fields that may be updated. All optional."""
    photo: Optional[str] = Field(None, max_length=255)
    date: Optional[date]
    description: Optional[str]

    @validator("photo")
    def must_be_valid_url(cls, v):
        if v and not (v.startswith("http://") or v.startswith("https://")):
            raise ValueError("Photo must be a valid URL (http or https)")
        return v

class EventInDB(EventBase):
    """Fields stored in the database."""
    id: int

    class Config:
        orm_mode = True

class EventResponse(BaseModel):
    """Standard response wrap for a single event."""
    status: str = "success"
    message: str
    event: EventInDB

class EventsListResponse(BaseModel):
    """Standard response wrap for multiple events."""
    status: str = "success"
    message: str
    events: list[EventInDB]
