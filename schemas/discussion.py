import datetime
from typing import List
from pydantic import BaseModel, Field


# -------------------------------
# Schema for sending a discussion message
# -------------------------------
class CreateDiscussionSchema(BaseModel):
    message: str = Field(..., min_length=1, description="The message text")

    class Config:
        json_schema_extra = {
            "example": {"message": "Welcome to the mentorship chat!"}
        }


# -------------------------------
# Response schema for a single message
# -------------------------------
class DiscussionSchema(BaseModel):
    id: int
    user_id: int
    message: str
    created_at: datetime.datetime

    model_config = {"from_attributes": True}


# -------------------------------
# Response schema for list (no pagination)
# -------------------------------
class DiscussionListResponse(BaseModel):
    total: int
    items: List[DiscussionSchema]

    model_config = {"from_attributes": True}
