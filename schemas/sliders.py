import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, validator

# ----------------------------------------
# Schema for creating a Slider
# ----------------------------------------
class CreateSliderSchema(BaseModel):
    description: str = Field(..., min_length=5, description="Slider description (min 5 characters)")

    @validator("description")
    def not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Description must not be blank")
        return v

# ----------------------------------------
# Schema for returning a single Slider
# ----------------------------------------
class SliderSchema(BaseModel):
    id: int
    photo: str
    description: str
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = {"from_attributes": True}

# ----------------------------------------
# Schema for paginated list of Sliders
# ----------------------------------------
class SliderListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    next_page: Optional[str]
    prev_page: Optional[str]
    items: List[SliderSchema]

    model_config = {"from_attributes": True}
