import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator

class CreateNewsSchema(BaseModel):
    title: str = Field(..., min_length=5, description="Headline of the news item")
    date: datetime.date = Field(..., description="Publication date of the news")
    description: str = Field(..., min_length=10, description="Full news description")

    @field_validator("date")
    def date_not_in_future(cls, v: datetime.date) -> datetime.date:
        if v > datetime.date.today():
            raise ValueError("News date cannot be in the future")
        return v

class NewsSchema(BaseModel):
    id: int
    title: str
    date: datetime.date
    description: str
    photo: str
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = {
        "from_attributes": True
    }

class NewsListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    next_page: Optional[str]
    prev_page: Optional[str]
    items: List[NewsSchema]

    model_config = {
        "from_attributes": True
    }