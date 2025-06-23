import datetime
from typing import List, Optional
from pydantic import BaseModel, Field

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
