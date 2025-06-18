import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator, validator

class CreateNewsSchema(BaseModel):
    title: str = Field(..., min_length=5, description="News title")
    date: datetime.date = Field(..., description="Date of the news item")
    description: str = Field(..., min_length=10, description="News description")

    # @field_validator("date")
    # def date_not_in_future(cls, v: datetime.date) -> datetime.date:
    #     # Latest news date should not be in the future
    #     if v > datetime.date.today():
    #         raise ValueError("News date cannot be in the future")
    #     return v

class LatestNewsSchema(BaseModel):
    id: int
    title: str
    date: datetime.date
    description: str
    photo: str               # fully qualified URL
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = {
        "from_attributes": True
    }

class LatestNewsListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    next_page: Optional[str]
    prev_page: Optional[str]
    items: List[LatestNewsSchema]

    model_config = {
        "from_attributes": True
    }
