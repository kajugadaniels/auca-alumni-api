from typing import List, Optional
from datetime import date
from pydantic import BaseModel

class UpcomingEventSchema(BaseModel):
    id: int
    photo: str
    date: date
    description: str

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
