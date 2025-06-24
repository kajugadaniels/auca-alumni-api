import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, validator

# ----------------------------------------
# Nested user info returned in histories
# ----------------------------------------
class UserInfoSchema(BaseModel):
    id: int
    email: str
    first_name: Optional[str]
    last_name: Optional[str]
    phone_number: Optional[str]

    model_config = {"from_attributes": True}

# ----------------------------------------
# Schema for a single history entry
# ----------------------------------------
class OpportunityHistorySchema(BaseModel):
    id: int
    opportunity_id: int
    user: UserInfoSchema
    comment: str
    status: str
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = {"from_attributes": True}

# ----------------------------------------
# Schema for paginated list
# ----------------------------------------
class OpportunityHistoryListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    next_page: Optional[str]
    prev_page: Optional[str]
    items: List[OpportunityHistorySchema]

    model_config = {"from_attributes": True}

# ----------------------------------------
# Schema for create/update payload
# ----------------------------------------
class CreateHistorySchema(BaseModel):
    opportunity_id: int = Field(..., gt=0, description="Existing opportunity ID")
    user_id: int = Field(..., gt=0, description="Existing user ID")
    comment: str = Field(..., min_length=5, description="Comment text")
    status: str = Field(..., description="Status text")

    @validator("comment")
    def comment_not_blank(cls, v):
        if not v.strip():
            raise ValueError("Comment must not be blank")
        return v.strip()

class OpportunityInfoSchema(BaseModel):
    id: int
    title: str
    description: str
    date: datetime.date

    model_config = {"from_attributes": True}