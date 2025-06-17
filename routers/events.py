from models import *
from schemas.* import *
from database import get_db
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import asc, desc, func
from fastapi import APIRouter, Depends, HTTPException, Query, Request

router = APIRouter()

@router.get(
    "/events",
    response_model=UpcomingEventListResponse,
    summary="Retrieve a paginated list of upcoming events with metadata and navigation URLs",
)
def get_upcoming_events(
    request: Request,
    *,
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Filter by description or title"),
    sort_by: str = Query(
        "date",
        regex="^(id|date|created_at)$",
        description="Field to sort by",
    ),
    order: str = Query("asc", regex="^(asc|desc)$", description="Sort direction"),
) -> UpcomingEventListResponse:
    """
    Retrieve upcoming events with:
    - total count of all records in the DB
    - current page and page_size
    - next_page and prev_page full URLs
    """
    # 1) Count total events (no filter)
    total = db.query(func.count(UpComingEvents.id)).scalar()

    # 2) Build filtered + ordered query
    query = db.query(UpComingEvents).filter(UpComingEvents.date >= func.current_date())
    if search:
        term = f"%{search.strip()}%"
        query = query.filter(UpComingEvents.description.ilike(term))

    direction = asc if order == "asc" else desc
    column = getattr(UpComingEvents, sort_by)
    query = query.order_by(direction(column))

    # 3) Apply pagination
    offset = (page - 1) * page_size
    items = query.offset(offset).limit(page_size).all()

    if not items and page != 1:
        raise HTTPException(status_code=404, detail="Page out of range")

    # 4) Build nav URLs
    def make_url(p: int) -> str:
        return str(request.url.include_query_params(page=p, page_size=page_size))

    prev_page = make_url(page - 1) if page > 1 else None
    next_page = make_url(page + 1) if offset + len(items) < total else None

    return UpcomingEventListResponse(
        total=total,
        page=page,
        page_size=page_size,
        next_page=next_page,
        prev_page=prev_page,
        items=items,
    )
