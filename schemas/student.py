from typing import List, Optional
from pydantic import BaseModel

class StudentSchema(BaseModel):
    id: int
    id_number: int
    first_name: str
    last_name: str

    model_config = {
        "from_attributes": True
    }

class StudentListResponse(BaseModel):
    total: int  # total students in the DB
    page: int
    page_size: int
    next_page: Optional[str]
    prev_page: Optional[str]
    items: List[StudentSchema]

    model_config = {
        "from_attributes": True
    }