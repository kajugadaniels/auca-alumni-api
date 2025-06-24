import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, validator
from schemas.auth import UserResponseSchema

# ----------------------------------------
# Input schema for creating/updating personal info
# ----------------------------------------
class CreatePersonalInformationSchema(BaseModel):
    bio: str = Field(..., min_length=10, description="Short biography")
    current_employer: Optional[str] = Field(None, description="Current employer")
    self_employed: Optional[str] = Field(None, description="Self-employed status")
    latest_education_level: Optional[str] = Field(None, description="Highest education level")
    address: str = Field(..., min_length=5, description="Address")
    profession_id: Optional[int] = Field(None, description="Profession FK")
    user_id: int = Field(..., gt=0, description="User FK")
    dob: Optional[datetime.date] = Field(None, description="Date of birth")
    start_date: Optional[datetime.date] = Field(None, description="Start date")
    end_date: Optional[datetime.date] = Field(None, description="End date")
    faculty_id: Optional[int] = Field(None, description="Faculty FK")
    country_id: Optional[str] = Field(None, description="Country code FK")
    department: Optional[str] = Field(None, description="Department")
    gender: bool = Field(..., description="Gender: True=Male, False=Female")
    status: Optional[str] = Field(None, description="Current status")

    @validator("bio", "address")
    def not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Field must not be blank")
        return v

# ----------------------------------------
# Output schema, includes nested user info
# ----------------------------------------
class PersonalInformationSchema(BaseModel):
    id: int
    photo: str               # fully qualified URL
    bio: str
    current_employer: Optional[str]
    self_employed: Optional[str]
    latest_education_level: Optional[str]
    address: str
    profession_id: Optional[int]
    user: UserResponseSchema
    dob: Optional[datetime.date]
    start_date: Optional[datetime.date]
    end_date: Optional[datetime.date]
    faculty_id: Optional[int]
    country_id: Optional[str]
    department: Optional[str]
    gender: bool
    status: Optional[str]
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = {"from_attributes": True}

# ----------------------------------------
# Paginated list response
# ----------------------------------------
class PersonalInformationListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    next_page: Optional[str]
    prev_page: Optional[str]
    items: List[PersonalInformationSchema]

    model_config = {"from_attributes": True}
