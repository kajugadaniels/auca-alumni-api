"""
Pydantic schema for Country model response.
"""
from pydantic import BaseModel, Field

class CountrySchema(BaseModel):
    id: int = Field(..., description="Unique country identifier")
    name: str = Field(..., description="Country name")
    abbreviation: str | None = Field(None, description="ISO abbreviation")
    currency: str | None = Field(None, description="Local currency")
    code: str | None = Field(None, description="Country code")

    model_config = {"from_attributes": True}
