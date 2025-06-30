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

# ----------------------------------------
# Update current user's account & profile
# ----------------------------------------
class UpdateProfileSchema(BaseModel):
    # --- Account fields ---
    email: Optional[EmailStr] = Field(None, description="New email address")
    phone_number: Optional[str] = Field(
        None, description="New phone number in international format"
    )

    # --- Personal information fields ---
    bio: Optional[str] = Field(None, description="Short biography or personal statement")
    current_employer: Optional[str] = Field(None, description="Current employer name")
    self_employed: Optional[str] = Field(None, description="Self-employment details")
    latest_education_level: Optional[str] = Field(
        None, description="Highest education level achieved"
    )
    address: Optional[str] = Field(None, description="Current mailing address")
    profession_id: Optional[int] = Field(None, description="ID of the profession")
    dob: Optional[datetime.date] = Field(None, description="Date of birth")
    start_date: Optional[datetime.date] = Field(None, description="Profile start date")
    end_date: Optional[datetime.date] = Field(None, description="Profile end date")
    faculty_id: Optional[int] = Field(None, description="ID of the faculty")
    country_id: Optional[str] = Field(None, description="ISO code of the country")
    department: Optional[str] = Field(None, description="Department name")
    gender: Optional[bool] = Field(None, description="Gender: true for male, false for female")
    status: Optional[str] = Field(None, description="Current status info")

    @validator("phone_number")
    def validate_phone(cls, v):
        if v is None:
            return v
        if not re.match(r"^\+?[1-9]\d{1,14}$", v):
            raise ValueError("Invalid phone number format")
        return v

    @validator("end_date")
    def check_dates(cls, v, values):
        start = values.get("start_date")
        if v and start and v < start:
            raise ValueError("end_date cannot be earlier than start_date")
        return v

    class Config:
        schema_extra = {
            "example": {
                "email": "jane.doe@example.com",
                "phone_number": "+250788123456",
                "bio": "AUCA alum and software engineer.",
                "current_employer": "TechCorp",
                "self_employed": None,
                "latest_education_level": "MSc Computer Science",
                "address": "123 Avenue, Kigali",
                "profession_id": 4,
                "dob": "1990-05-15",
                "start_date": "2025-01-01",
                "end_date": None,
                "faculty_id": 2,
                "country_id": "RWA",
                "department": "Computer Science",
                "gender": True,
                "status": "Active"
            }
        }