import datetime
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, Field, validator


# ----------- inbound ------------
class CreateDonationSchema(BaseModel):
    name: str = Field(..., min_length=2, description="Donor full name")
    email: str = Field(..., description="Donor email address")
    amount: Decimal = Field(..., gt=0, description="Donation amount (≥ 0.01)")
    message: Optional[str] = Field(None, description="Optional note from donor")

    # quick sanity-check
    @validator("name")
    def name_not_blank(cls, v):  # noqa: N805
        if not v.strip():
            raise ValueError("Name must not be blank")
        return v.strip()


# ----------- single out -----------
class DonationSchema(BaseModel):
    id: int
    user_id: int
    name: str
    email: str
    amount: Decimal
    message: Optional[str]
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = {"from_attributes": True}


# ----------- list out ------------
class DonationListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    next_page: Optional[str]
    prev_page: Optional[str]
    items: List[DonationSchema]

    model_config = {"from_attributes": True}