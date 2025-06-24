import datetime
from typing import List, Optional
from pydantic import BaseModel, Field

# ----------------------------------------
# Create / Update DTO
# ----------------------------------------
class CreateCertificationSchema(BaseModel):
    user_id: int = Field(..., gt=0, description="ID of the associated user")
    certificate_name: str = Field(..., min_length=3, description="Name of the certification")
    year: int = Field(..., ge=1900, le=datetime.date.today().year, description="Year obtained")
    type: str = Field(..., min_length=3, description="Certification type or category")
    description: str = Field(..., min_length=10, description="Detailed description")
    image: bytes = Field(..., description="Binary image data for the certificate")

# ----------------------------------------
# Nested User DTO
# ----------------------------------------
class UserNestedSchema(BaseModel):
    id: int
    email: str
    first_name: str
    last_name: str
    phone_number: Optional[str]

    model_config = {"from_attributes": True}

# ----------------------------------------
# Certification Response DTO
# ----------------------------------------
class CertificationSchema(BaseModel):
    id: int
    user: UserNestedSchema
    certificate_name: str
    year: int
    type: str
    description: str
    image: str                    # fully qualified URL
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = {"from_attributes": True}

# ----------------------------------------
# List Response DTO
# ----------------------------------------
class CertificationListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    next_page: Optional[str]
    prev_page: Optional[str]
    items: List[CertificationSchema]

    model_config = {"from_attributes": True}
