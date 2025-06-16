"""
Combined schema definitions for authentication: user registration, login, and token models.
"""
import re
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, validator

# Login User

class LoginSchema(BaseModel):
    username: str = Field(..., description="Email or phone number")
    password: str = Field(..., description="User password")

class TokenSchema(BaseModel):
    access_token: str
    token_type: str = "bearer"

class UserResponseSchema(BaseModel):
    id: int
    email: EmailStr
    student_id: int
    first_name: str
    last_name: str
    phone_number: str

    model_config = {"from_attributes": True}

# Register User

class UserRegisterSchema(BaseModel):
    email: EmailStr = Field(..., description="Valid email address")
    password: str = Field(..., min_length=8, description="Password (min 8 characters)")
    student_id: int = Field(..., gt=0, description="Existing student ID from Students table")
    phone_number: str = Field(..., description="Phone number in international format, e.g. +250788123456")

    @validator('password')
    def password_strength(cls, v):
        # ensure password has both letters and numbers
        if v.isdigit() or v.isalpha():
            raise ValueError("Password must contain both letters and numbers")
        return v

    @validator('phone_number')
    def valid_phone(cls, v):
        # E.164 international phone number format
        pattern = re.compile(r"^\+?[1-9]\d{1,14}$")
        if not pattern.match(v):
            raise ValueError("Invalid phone number format")
        return v

class VerifyTokenResponse(BaseModel):
    status: str
    message: str
    user: UserResponseSchema

class LogoutResponse(BaseModel):
    status: str
    message: str