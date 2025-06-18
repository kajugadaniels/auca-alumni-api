import datetime
from typing import List, Optional
from pydantic import BaseModel, Field

class NewsSchema(BaseModel):
    id: int
    title: str
    date: datetime.date
    description: str
    photo: str  # full URL to the news image
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
