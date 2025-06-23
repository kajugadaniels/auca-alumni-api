"""
Combined schema definitions for authentication and OTP-driven registration.
"""
import re
import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, validator

# ----------------------------------------
# Login User
# ----------------------------------------
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


# ----------------------------------------
# 1) Registration Initiation
#    (POST /api/auth/register/initiate)
# ----------------------------------------
class RegistrationInitiateSchema(BaseModel):
    student_id: int = Field(..., gt=0, description="Existing student ID from Students table")
    email: EmailStr = Field(..., description="Valid email address")
    phone_number: str = Field(..., description="Phone number in international format, e.g. +250788123456")

    @validator("phone_number")
    def valid_phone(cls, v):
        pattern = re.compile(r"^\+?[1-9]\d{1,14}$")
        if not pattern.match(v):
            raise ValueError("Invalid phone number format")
        return v


# ----------------------------------------
# 2) Registration Completion
#    (POST /api/auth/register/complete)
# ----------------------------------------
class RegistrationCompleteSchema(BaseModel):
    student_id: int = Field(..., gt=0, description="Existing student ID from Students table")
    otp: str = Field(..., min_length=6, max_length=6, description="6-digit OTP code sent via email")
    password: str = Field(..., min_length=8, description="Password (min 8 characters)")
    confirm_password: str = Field(..., min_length=8, description="Password confirmation")

    @validator("password")
    def password_strength(cls, v):
        if v.isdigit() or v.isalpha():
            raise ValueError("Password must contain both letters and numbers")
        return v

    @validator("confirm_password")
    def passwords_match(cls, v, values):
        pwd = values.get("password")
        if pwd and v != pwd:
            raise ValueError("Passwords do not match")
        return v


# ----------------------------------------
# Legacy: combined Register schema (optional)
# ----------------------------------------
class UserRegisterSchema(BaseModel):
    student_id: int = Field(..., gt=0, description="Existing student ID from Students table")
    email: EmailStr = Field(..., description="Valid email address")
    phone_number: str = Field(..., description="Phone number in international format, e.g. +250788123456")
    password: str = Field(..., min_length=8, description="Password (min 8 characters)")

    @validator("password")
    def password_strength(cls, v):
        if v.isdigit() or v.isalpha():
            raise ValueError("Password must contain both letters and numbers")
        return v

    @validator("phone_number")
    def valid_phone(cls, v):
        pattern = re.compile(r"^\+?[1-9]\d{1,14}$")
        if not pattern.match(v):
            raise ValueError("Invalid phone number format")
        return v


# ----------------------------------------
# Token verification & logout
# ----------------------------------------
class VerifyTokenResponse(BaseModel):
    status: str
    message: str
    user: UserResponseSchema


class LogoutResponse(BaseModel):
    status: str
    message: str
