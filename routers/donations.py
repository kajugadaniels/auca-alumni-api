from decimal import Decimal
from typing import List

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Request,
    status,
)
from sqlalchemy.orm import Session
from sqlalchemy import desc, func

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

@router.get(
    "/",
    response_model=DonationListResponse,
    summary="Retrieve all donations (latest first)",
)
# ------------------------------ GET all ------------------------------ #
def list_donations(
    request: Request,
    *,
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
) -> DonationListResponse:
    """
    Returns a paginated list of donations, ordered by most-recent first.
    """
    # total count
    total = db.query(func.count(Donations.id)).scalar()

    # ordering + pagination
    query = db.query(Donations).order_by(desc(Donations.created_at))
    offset = (page - 1) * page_size
    records = query.offset(offset).limit(page_size).all()

    if not records and page != 1:
        raise HTTPException(status_code=404, detail="Page out of range")

    # helper for nav URLs
    def make_url(p: int) -> str:
        return str(request.url.include_query_params(page=p, page_size=page_size))

    prev_page = make_url(page - 1) if page > 1 else None
    next_page = make_url(page + 1) if offset + len(records) < total else None

    return DonationListResponse(
        total=total,
        page=page,
        page_size=page_size,
        prev_page=prev_page,
        next_page=next_page,
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
