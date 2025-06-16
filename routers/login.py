
from models import *
from schemas.login import *
from utils.security import *
from database import get_db
from sqlalchemy.orm import Session
from fastapi.responses import JSONResponse
from fastapi import APIRouter, Depends, HTTPException, status, Body

router = APIRouter()
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