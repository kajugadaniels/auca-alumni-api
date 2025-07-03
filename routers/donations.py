from decimal import Decimal
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import desc

from database import get_db
from models import Donations
from schemas.donation import (
    CreateDonationSchema,
    DonationSchema,
    DonationListResponse,
)
from routers.auth import get_current_user

router = APIRouter(
    prefix="/donations",
    tags=["donations"],
    dependencies=[Depends(get_current_user)],  # all endpoints require auth
)


# ------------------------------ GET all ------------------------------ #
@router.get(
    "/",
    response_model=DonationListResponse,
    summary="Retrieve all donations (latest first)",
)
def list_donations(
    db: Session = Depends(get_db),
) -> DonationListResponse:
    records: List[Donations] = (
        db.query(Donations).order_by(desc(Donations.created_at)).all()
    )
    return DonationListResponse(
        total=len(records),
        items=records,
    )


# ------------------------------ POST add ----------------------------- #
@router.post(
    "/add",
    response_model=DonationSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new donation",
)
def create_donation(
    payload: CreateDonationSchema,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> DonationSchema:
    """
    Creates a donation record.  
    `user_id` is **always** taken from the authenticated user.
    """
    new_row = Donations(
        user_id=current_user.id,
        name=payload.name.strip(),
        email=payload.email.strip(),
        amount=Decimal(payload.amount),
        message=payload.message.strip() if payload.message else None,
    )
    db.add(new_row)
    db.commit()
    db.refresh(new_row)
    return new_row
