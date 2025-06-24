import datetime
from typing import List, Optional
from pydantic import BaseModel, Field

# ----------------------------------------
# Create / Update DTO
# ----------------------------------------
class CreateDepartmentSchema(BaseModel):
    faculty_id: int = Field(..., gt=0, description="ID of the parent faculty")
    name: str = Field(..., min_length=2, description="Name of the department")

# ----------------------------------------
# Nested Faculty DTO
# ----------------------------------------
class FacultyNestedSchema(BaseModel):
    id: int
    name: str

    model_config = {"from_attributes": True}

# ----------------------------------------
# Department Response DTO
# ----------------------------------------
class DepartmentSchema(BaseModel):
    id: int
    faculty: FacultyNestedSchema
    name: str
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = {"from_attributes": True}

# ----------------------------------------
# List Response DTO
# ----------------------------------------
class DepartmentListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    next_page: Optional[str]
    prev_page: Optional[str]
    items: List[DepartmentSchema]

    model_config = {"from_attributes": True}
