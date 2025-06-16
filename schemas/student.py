from typing import List, Optional
from pydantic import BaseModel

class StudentSchema(BaseModel):
    id: int
    id_number: int
    first_name: str
    last_name: str

    class Config:
        orm_mode = True

class StudentListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    next_page: Optional[int]
    prev_page: Optional[int]
    items: List[StudentSchema]