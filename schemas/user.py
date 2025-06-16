from pydantic import BaseModel, EmailStr, Field, validator

class UserRegisterSchema(BaseModel):
    email: EmailStr = Field(..., description="Valid email address")
    password: str = Field(..., min_length=8, description="Password (min 8 characters)")
    student_id: int = Field(..., gt=0, description="Existing student ID")
    first_name: str = Field(..., min_length=1, description="Your first name")
    last_name: str = Field(..., min_length=1, description="Your last name")

    @validator("password")
    def password_strength(cls, v):
        if v.isdigit() or v.isalpha():
            raise ValueError("Password must contain both letters and numbers")
        return v

class UserResponseSchema(BaseModel):
    id: int
    email: EmailStr
    student_id: int
    first_name: str
    last_name: str

    model_config = {"from_attributes": True}
