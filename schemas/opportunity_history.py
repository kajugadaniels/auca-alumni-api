import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

class CreateOpportunityHistorySchema(BaseModel):
    opportunity_id: int = Field(..., gt=0, description="ID of the related opportunity")
    user_id: int = Field(..., gt=0, description="ID of the user making the comment")
    comment: str = Field(..., min_length=5, description="Comment text")
    status: str = Field(..., description="Status update for this history entry")

class OpportunityUserSchema(BaseModel):
    id: int
    first_name: str
    last_name: str
    email: str

    model_config = {"from_attributes": True}

class OpportunitySummarySchema(BaseModel):
    id: int
    title: str

    model_config = {"from_attributes": True}

class OpportunityHistorySchema(BaseModel):
    id: int
    comment: str
    status: str
    created_at: datetime.datetime
    updated_at: datetime.datetime
    user: OpportunityUserSchema
    opportunity: OpportunitySummarySchema

    model_config = {"from_attributes": True}

class OpportunityHistoryListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    next_page: Optional[str]
    prev_page: Optional[str]
    items: List[OpportunityHistorySchema]

    model_config = {"from_attributes": True}
