import datetime
from typing import List, Optional
from pydantic import BaseModel, Field

# ----------------------------------------
# Create DTO
# ----------------------------------------
class CreateExecutiveCommitteeSchema(BaseModel):
    name: str = Field(..., min_length=3, description="Committee member's full name")
    position: str = Field(..., min_length=2, description="Member's position/title")
    photo: bytes = Field(..., description="Binary image data for the member photo")

# ----------------------------------------
# Response DTO for a single record
# ----------------------------------------
class ExecutiveCommitteeSchema(BaseModel):
    id: int
    name: str
    position: str
    photo: str                    # fully-qualified URL
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = {"from_attributes": True}

# ----------------------------------------
# List Response DTO
# ----------------------------------------
class ExecutiveCommitteeListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    next_page: Optional[str]
    prev_page: Optional[str]
    items: List[ExecutiveCommitteeSchema]

    model_config = {"from_attributes": True}
