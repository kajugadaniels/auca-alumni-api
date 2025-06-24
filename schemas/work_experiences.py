import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, validator, PositiveInt

from schemas.auth import UserResponseSchema

# ----------------------------------------
# Schema for creating a Work Experience
# ----------------------------------------
class CreateWorkExperienceSchema(BaseModel):
    company: str = Field(..., min_length=2, description="Company name")
    employer: str = Field(..., min_length=2, description="Employer/manager name")
    job_title: str = Field(..., min_length=2, description="Job title")
    job_description: str = Field(..., min_length=10, description="Job description")
    start_date: datetime.date = Field(..., description="Start date")
    end_date: Optional[str] = Field(None, description="End date or ongoing")
    user_id: PositiveInt = Field(..., description="ID of the user this experience belongs to")

    @validator("company", "employer", "job_title", "job_description")
    def not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Field must not be blank")
        return v

# ----------------------------------------
# Schema for returning a single Work Experience
# ----------------------------------------
class WorkExperienceSchema(BaseModel):
    id: int
    company: str
    employer: str
    job_title: str
    job_description: str
    start_date: datetime.date
    end_date: Optional[str]
    created_at: datetime.datetime
    updated_at: datetime.datetime
    user: UserResponseSchema

    model_config = {"from_attributes": True}

# ----------------------------------------
# Schema for paginated list of Work Experiences
# ----------------------------------------
class WorkExperienceListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    next_page: Optional[str]
    prev_page: Optional[str]
    items: List[WorkExperienceSchema]

    model_config = {"from_attributes": True}
