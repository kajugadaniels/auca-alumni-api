from typing import Optional
from pydantic import BaseModel, Field, EmailStr

class LoginSchema(BaseModel):
    username: str = Field(..., description="Email or phone number")
    password: str = Field(..., description="User password")

class TokenSchema(BaseModel):
    access_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    user_id: Optional[int] = None