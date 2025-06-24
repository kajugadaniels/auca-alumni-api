import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, validator, HttpUrl

# ----------------------------------------
# Schema for the nested user info
# ----------------------------------------
class OpportunityUserSchema(BaseModel):
    id: int
    email: str
    first_name: str
    last_name: str
    phone_number: str
    student_id: int

    model_config = {"from_attributes": True}


# ----------------------------------------
# Schema for creating an Opportunity
# ----------------------------------------
class CreateOpportunitySchema(BaseModel):
    title: str = Field(..., min_length=5, description="Opportunity title (min 5 chars)")
    description: str = Field(..., min_length=10, description="Opportunity description")
    date: datetime.date = Field(..., description="Date of the opportunity")
    user_id: int = Field(..., gt=0, description="Existing user ID")
    status: Optional[str] = Field(None, description="Opportunity status")
    link: Optional[str] = Field(None, description="External link for more info")

    @validator("title", "description")
    def not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Must not be blank")
        return v


# ----------------------------------------
# Schema for returning a single Opportunity
# ----------------------------------------
class OpportunitySchema(BaseModel):
    id: int
    photo: HttpUrl
    title: str
    description: str
    date: datetime.date
    status: Optional[str]
    link: Optional[str]
    created_at: datetime.datetime
    updated_at: datetime.datetime
    user: OpportunityUserSchema

    model_config = {"from_attributes": True}


# ----------------------------------------
# Schema for paginated list of Opportunities
# ----------------------------------------
class OpportunityListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    next_page: Optional[str]
    prev_page: Optional[str]
    items: List[OpportunitySchema]

    model_config = {"from_attributes": True}
