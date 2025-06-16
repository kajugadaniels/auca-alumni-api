from typing import List, Optional
from pydantic import BaseModel

class StudentSchema(BaseModel):
    id: int
    id_number: int
    first_name: str
    last_name: str

    model_config = {
        "from_attributes": True  # enable attribute-based loading (ORM mode) in Pydantic v2
    }

class StudentListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    next_page: Optional[int]
    prev_page: Optional[int]
    items: List[StudentSchema]

    model_config = {
        "from_attributes": True
    }
