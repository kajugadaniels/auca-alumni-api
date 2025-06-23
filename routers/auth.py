import os
import random
import smtplib
from email.message import EmailMessage
from fastapi import APIRouter, Depends, HTTPException, status, Body
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from passlib.context import CryptContext

from database import get_db
from models import Users, Students
from schemas.auth import (
    UserRegisterSchema,
    UserResponseSchema,
    LoginSchema,
    TokenSchema,
    VerifyTokenResponse,
    LogoutResponse,
)
from utils.security import create_access_token, verify_password, decode_access_token
from fastapi.security import OAuth2PasswordBearer

# Load SMTP creds from env
EMAIL_HOST = os.getenv("EMAIL_HOST")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", 587))
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "True") == "True"
EMAIL_USER = os.getenv("EMAIL_HOST_USER")
EMAIL_PASS = os.getenv("EMAIL_HOST_PASSWORD")

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

# Register

def send_otp_email(recipient: str, otp: str):
    """
    Send the OTP via Gmail SMTP.
    """
    msg = EmailMessage()
    msg["Subject"] = "Your AUCA Alumni Registration OTP"
    msg["From"] = EMAIL_USER
    msg["To"] = recipient
    msg.set_content(f"Your OTP code is: {otp}\nThis code will expire in 15 minutes.")

    with smtplib.SMTP(EMAIL_HOST, EMAIL_PORT) as server:
        if EMAIL_USE_TLS:
            server.starttls()
        server.login(EMAIL_USER, EMAIL_PASS)
        server.send_message(msg)

# ------------------------------------------------------------------------
# STEP 1: Initiate registration by sending OTP
# ------------------------------------------------------------------------
@router.post(
    "/register/initiate",
    status_code=status.HTTP_200_OK,
    summary="Initiate registration: verify student and send OTP to email",
)
def initiate_registration(
    data: UserRegisterSchema = Body(
        ...,
        example={
            "email": "student@example.com",
            "student_id": 123,
            "phone_number": "+250788123456"
        },
    ),
    db: Session = Depends(get_db),
):
    """
    1) Verify student exists.
    2) Prevent duplicate user for same student or email.
    3) Generate 6-digit OTP, store in remember_token.
    4) Email OTP to the user.
    """
    # 1) Verify student exists
    student = db.query(Students).filter_by(id=data.student_id).first()
    if not student:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "invalid_student_id",
                "message": f"No student found with ID {data.student_id}."
            },
        )

    # 2) Prevent duplicate
    existing = (
        db.query(Users)
        .filter((Users.email == data.email) | (Users.student_id == data.student_id))
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "already_registered",
                "message": "A user with this student ID or email already exists."
            },
        )

    # 3) Create placeholder user with OTP in remember_token
    otp = f"{random.randint(0, 999999):06d}"
    new_user = Users(
        email=data.email,
        password="",                      # will set later
        student_id=data.student_id,
        phone_number=data.phone_number,
        first_name=student.first_name,
        last_name=student.last_name,
        remember_token=otp,               # store OTP here
    )
    db.add(new_user)
    db.commit()

    # 4) Send the OTP email
    try:
        send_otp_email(data.email, otp)
    except Exception as e:
        # Roll back user creation on email failure
        db.delete(new_user)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "email_failed",
                "message": "Failed to send OTP email. Please try again later."
            },
        )

    return {"status": "success", "message": "OTP sent to email. Please check your inbox."}

# ------------------------------------------------------------------------
# STEP 2: Complete registration by verifying OTP and setting password
# ------------------------------------------------------------------------
@router.post(
    "/register/complete",
    status_code=status.HTTP_201_CREATED,
    summary="Complete registration: verify OTP and set password",
)
def complete_registration(
    student_id: int = Body(..., embed=True),
    otp: str = Body(..., embed=True, description="6-digit code sent via email"),
    password: str = Body(..., embed=True, min_length=8, description="Password"),
    confirm_password: str = Body(..., embed=True, min_length=8, description="Confirm password"),
    db: Session = Depends(get_db),
):
    """
    1) Find user by student_id and matching OTP in remember_token.
    2) Validate OTP and passwords match.
    3) Hash password, clear OTP, set created_at/updated_at.
    4) Return user info.
    """
    # 1) Lookup user
    user = db.query(Users).filter_by(student_id=student_id, remember_token=otp).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "invalid_otp", "message": "OTP is invalid or expired."},
        )

    # 2) Validate passwords
    if password != confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "password_mismatch", "message": "Passwords do not match."},
        )
    if password.isalpha() or password.isdigit():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "weak_password", "message": "Password must contain letters and numbers."},
        )

    # 3) Hash and persist
    hashed_pw = pwd_context.hash(password)
    user.password = hashed_pw
    user.remember_token = None             # clear OTP
    db.add(user)
    db.commit()
    db.refresh(user)

    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={
            "status": "success",
            "message": "Registration complete. You can now log in.",
            "user": {
                "id": user.id,
                "email": user.email,
                "student_id": user.student_id,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "phone_number": user.phone_number,
            },
        },
    )

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

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    "Validate token, check revocation, and return user."  
    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "invalid_token", "message": "Token invalid or expired."},
            headers={"WWW-Authenticate": "Bearer"},
        )
    # check if token has been revoked
    jti = payload.get("jti")
    if db.query(RevokedToken).filter_by(jti=jti).first():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "token_revoked", "message": "Token has been revoked. Please login again."},
            headers={"WWW-Authenticate": "Bearer"},
        )
    user_id = int(payload["sub"])
    user = db.query(Users).get(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "user_not_found", "message": "User not found."},
            headers={"WWW-Authenticate": "Bearer"},
        )
    return {"user": user, "jti": jti}

@router.get(
    "/verify-token",
    response_model=VerifyTokenResponse,
    summary="Verify access token validity",
)
def verify_token(
    current_user: Users = Depends(get_current_user)
):
    """
    Endpoint to check if a token is valid. Returns the current user's basic info.
    Expired tokens will be rejected by the dependency.
    """
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": "success",
            "message": "Token is valid.",
            "user": {
                "id": current_user.id,
                "email": current_user.email,
                "first_name": current_user.first_name,
                "last_name": current_user.last_name,
                "student_id": current_user.student_id,
                "phone_number": current_user.phone_number,
            },
        },
    )

@router.post(
    "/logout",
    response_model=LogoutResponse,
    summary="Revoke current user's token",
)
def logout(current=Depends(get_current_user), db: Session = Depends(get_db)):
    """Revokes the JWT by storing its JTI in a blacklist table."""
    context = current  # dictionary with 'user' and 'jti'
    # persist revoked token
    revoked = RevokedToken(jti=context['jti'])
    db.add(revoked)
    db.commit()
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"status": "success", "message": "Logout successful; token revoked."},
    )