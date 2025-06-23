import datetime
from typing import List, Optional
from pydantic import BaseModel, Field

class ProgramSchema(BaseModel):
    id: int
    title: str
    description: str
    photo: str               # fully qualified URL
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = {
        "from_attributes": True
    }

class ProgramListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    next_page: Optional[str]
    prev_page: Optional[str]
    items: List[ProgramSchema]

    model_config = {
        "from_attributes": True
    }
