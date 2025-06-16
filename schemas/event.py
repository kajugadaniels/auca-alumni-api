"""
Pydantic schemas for UpComingEvents CRUD operations.
"""
from datetime import date
from pydantic import BaseModel, Field, HttpUrl

class EventBase(BaseModel):
    photo: HttpUrl = Field(..., description="URL or path to the event photo (will be uploaded)")
    date: date = Field(..., description="Date of the event")
    description: str = Field(..., description="Detailed description of the event")

class EventCreate(EventBase):
    pass  # inherits all fields for creation

class EventUpdate(BaseModel):
    photo: HttpUrl | None = Field(None, description="Updated photo URL/path")
    date: date | None = Field(None, description="Updated event date")
    description: str | None = Field(None, description="Updated description")

class EventResponse(EventBase):
    id: int = Field(..., description="Unique event identifier")

    model_config = {"from_attributes": True}