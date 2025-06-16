import re
from pydantic import BaseModel, EmailStr, Field, validator

class UserRegisterSchema(BaseModel):
    email: EmailStr = Field(..., description="Valid email address")
    password: str = Field(..., min_length=8, description="Password (min 8 characters)")
    student_id: int = Field(..., gt=0, description="Existing student ID from Students table")
    phone_number: str = Field(..., description="Phone number in international format, e.g. +250788123456")

    @validator('password')
    def password_strength(cls, v):
        if v.isdigit() or v.isalpha():
            raise ValueError("Password must contain both letters and numbers")
        return v

    @validator('phone_number')
    def valid_phone(cls, v):
        pattern = re.compile(r"^\+?[1-9]\d{1,14}$")
        if not pattern.match(v):
            raise ValueError("Invalid phone number format")
        return v

class UserResponseSchema(BaseModel):
    id: int
    email: EmailStr
    student_id: int
    first_name: str
    last_name: str
    phone_number: str

    model_config = {"from_attributes": True}