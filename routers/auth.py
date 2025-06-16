"""
Authentication router: handles /auth/register and /auth/login
"""
from models import *
from schemas.auth import *
from database import get_db
from utils.security import *
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordBearer
from fastapi import APIRouter, Depends, HTTPException, status, Body

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

# Register

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
            detail={
                "error": "invalid_student_id",
                "message": f"No student found with ID {data.student_id}. Please check your Student ID."},
        )

    # 2) Prevent duplicate user for same student or email
    existing = (
        db.query(Users)
        .filter((Users.email == data.email) | (Users.student_id == data.student_id))
        .first()
    )
    if existing:
        if existing.email == data.email:
            code = "email_exists"
            msg = f"Email {data.email} is already registered. Forgot your password?"
        else:
            code = "student_registered"
            msg = f"A user is already registered with Student ID {data.student_id}."
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": code, "message": msg},
        )

    # 3) Hash password
    hashed_pw = pwd_context.hash(data.password)

    # 4) Create and persist user, using student name
    new_user = Users(
        email=data.email,
        password=hashed_pw,
        student_id=data.student_id,
        first_name=student.first_name,
        last_name=student.last_name,
        phone_number=data.phone_number,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={
            "status": "success",
            "message": "User registered successfully.",
            "user": {
                "id": new_user.id,
                "email": new_user.email,
                "student_id": new_user.student_id,
                "first_name": new_user.first_name,
                "last_name": new_user.last_name,
                "phone_number": new_user.phone_number,
            },
        },
    )

# Login

@router.post(
    "/login",
    response_model=TokenSchema,
    summary="User login to receive access token",
)
def login(
    data: LoginSchema = Body(..., media_type="application/json"),
    db: Session = Depends(get_db),
):
    """
    Authenticate user by email or phone_number and password via JSON payload.
    """
    # 1) Validate presence
    if not data.username or not data.password:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "status": "error",
                "message": "Username and password are required.",
                "errors": [
                    {"loc": ["body", "username"], "message": "Field required."},
                    {"loc": ["body", "password"], "message": "Field required."},
                ],
            },
        )
    # 2) Find user by email or phone_number
    user = (
        db.query(Users)
        .filter(
            (Users.email == data.username) |
            (Users.phone_number == data.username)
        )
        .first()
    )
    if not user or not verify_password(data.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "invalid_credentials", "message": "Incorrect username or password."},
            headers={"WWW-Authenticate": "Bearer"},
        )
    # 3) Create JWT
    access_token = create_access_token({"sub": str(user.id)})
    # 4) Return token
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": "success",
            "message": "Login successful.",
            "access_token": access_token,
            "token_type": "bearer"
        },
    )