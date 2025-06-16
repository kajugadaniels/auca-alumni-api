from models import *
from database import *
from schemas.user import *
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from fastapi import APIRouter, Depends, HTTPException, status

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

@router.post(
    "/register",
    response_model=UserResponseSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user linked to a student record",
)
def register_user(data: UserRegisterSchema, db: Session = Depends(get_db)):
    # 1) Verify student exists
    student = db.query(Students).filter_by(id=data.student_id).first()
    if not student:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Student with ID {data.student_id} does not exist.",
        )

    # 2) Prevent duplicate user for same student
    existing = (
        db.query(Users)
        .filter((Users.email == data.email) | (Users.student_id == data.student_id))
        .first()
    )
    if existing:
        field = "email" if existing.email == data.email else "student_id"
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"A user with this {field} is already registered.",
        )

    # 3) Hash password
    hashed_pw = pwd_context.hash(data.password)

    # 4) Create and persist user
    new_user = Users(
        email=data.email,
        password=hashed_pw,
        student_id=data.student_id,
        first_name=data.first_name,
        last_name=data.last_name,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user