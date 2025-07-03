import os
import random
import smtplib
from email.message import EmailMessage
from fastapi import APIRouter, Depends, HTTPException, status, Body, File, UploadFile
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordBearer

from database import get_db
from models import *
from schemas.auth import (
    RegistrationInitiateSchema,
    RegistrationCompleteSchema,
    UserRegisterSchema,
    UserResponseSchema,
    LoginSchema,
    TokenSchema,
    VerifyTokenResponse,
    LogoutResponse,
    UpdateProfileSchema,
)
from utils.security import create_access_token, verify_password, decode_access_token

# Load SMTP creds from env
EMAIL_HOST = os.getenv("EMAIL_HOST")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", 587))
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "True") == "True"
EMAIL_USER = os.getenv("EMAIL_HOST_USER")
EMAIL_PASS = os.getenv("EMAIL_HOST_PASSWORD")

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


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
    data: RegistrationInitiateSchema,
    db: Session = Depends(get_db),
):
    """
    1) Verify student exists.
    2) Prevent duplicate user for same student or email.
    3) Generate 6-digit OTP, store in remember_token.
    4) Email OTP to the user.
    """
    student = db.query(Students).filter_by(id=data.student_id).first()
    if not student:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "invalid_student_id",
                "message": f"No student found with ID {data.student_id}."
            },
        )

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

    otp = f"{random.randint(0, 999999):06d}"
    new_user = Users(
        email=data.email,
        password="",  # to be set later
        student_id=data.student_id,
        phone_number=data.phone_number,
        first_name=student.first_name,
        last_name=student.last_name,
        remember_token=otp,
    )
    db.add(new_user)
    db.commit()

    try:
        send_otp_email(data.email, otp)
    except Exception:
        db.delete(new_user)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "email_failed", "message": "Failed to send OTP email."},
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
    data: RegistrationCompleteSchema,
    db: Session = Depends(get_db),
):
    """
    1) Find user by student_id and matching OTP in remember_token.
    2) Validate OTP and passwords match.
    3) Hash password, clear OTP.
    4) Return user info.
    """
    user = db.query(Users).filter_by(student_id=data.student_id, remember_token=data.otp).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "invalid_otp", "message": "OTP is invalid or expired."},
        )

    hashed_pw = pwd_context.hash(data.password)
    user.password = hashed_pw
    user.remember_token = None
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
    # Check if token has been revoked
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
    return user

@router.get(
    "/verify-token",
    response_model=VerifyTokenResponse,
    summary="Verify access token validity and fetch full profile",
)
def verify_token(
    current_user: Users = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Check if the provided JWT is valid, then return both the
    user's core fields and any extended personal information.
    """
    # Attempt to load personal_information record, if it exists
    personal_info = (
        db.query(PersonalInformation)
        .filter(PersonalInformation.user_id == current_user.id)
        .first()
    )

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
                "personal_information": personal_info,  # may be None
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

@router.put(
    "/profile",
    status_code=status.HTTP_200_OK,
    summary="Update current user's account & personal data (no photo)",
)
def update_profile(
    data: UpdateProfileSchema = Body(...),
    current_user: Users = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    - JSON-only update of email, phone, bio, address, etc.
    - Upserts PersonalInformation: creates if missing (requires bio & address), otherwise updates.
    """
    user = db.get(Users, current_user.id)
    if data.email:
        user.email = data.email
    if data.phone_number:
        user.phone_number = data.phone_number
    db.add(user)

    pi = db.query(PersonalInformation).filter_by(user_id=user.id).first()
    # create if missing
    if not pi:
        if data.bio is None or data.address is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "error": "missing_fields",
                    "message": "Both 'bio' and 'address' are required to create your profile."
                },
            )
        pi = PersonalInformation(
            user_id=user.id,
            bio=data.bio,
            address=data.address,
            photo=None,
            current_employer=data.current_employer,
            self_employed=data.self_employed,
            latest_education_level=data.latest_education_level,
            profession_id=data.profession_id,
            dob=data.dob,
            start_date=data.start_date,
            end_date=data.end_date,
            faculty_id=data.faculty_id,
            country_id=data.country_id,
            department=data.department,
            gender=data.gender,
            status=data.status,
        )
    else:
        # update existing
        for field in (
            "bio", "address", "current_employer", "self_employed", "latest_education_level",
            "profession_id", "dob", "start_date", "end_date",
            "faculty_id", "country_id", "department", "gender", "status"
        ):
            val = getattr(data, field)
            if val is not None:
                setattr(pi, field, val)

    db.add(pi)
    db.commit()
    db.refresh(user)

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": "success",
            "message": "Your profile data has been saved.",
            "user": {
                "id": user.id,
                "email": user.email,
                "student_id": user.student_id,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "phone_number": user.phone_number,
                "photo_url": pi.photo,
            },
        },
    )


@router.put(
    "/profile/photo",
    status_code=status.HTTP_200_OK,
    summary="Upload or replace current user's profile photo",
)
async def update_profile_photo(
    photo: UploadFile = File(..., description="New profile photo (1270×720 will be auto-crop)"),
    current_user: Users = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    - Multipart form upload of a single 'photo' file.
    - Requires an existing PersonalInformation row; 404 if none.
    """
    pi = db.query(PersonalInformation).filter_by(user_id=current_user.id).first()
    if not pi:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No profile found; please create profile data before uploading a photo."
        )

    ext = os.path.splitext(photo.filename)[1] or ".jpg"
    filename = f"user_{current_user.id}_{int(datetime.datetime.utcnow().timestamp())}{ext}"
    dest = os.path.join(UPLOAD_DIR, filename)

    contents = await photo.read()
    buf = BytesIO(contents)
    try:
        img = Image.open(buf).convert("RGB").resize((1270, 720), Image.LANCZOS)
        img.save(dest, quality=85)
    except UnidentifiedImageError:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is not a valid image."
        )

    pi.photo = f"/uploads/personal_information/{filename}"
    db.add(pi)
    db.commit()

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": "success",
            "message": "Profile photo updated.",
            "photo_url": pi.photo,
        },
    )