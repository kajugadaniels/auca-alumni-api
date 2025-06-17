from models import UpComingEvents
from schemas.event import UpcomingEventListResponse, UpcomingEventSchema
from database import get_db
from typing import Optional
from datetime import date
from sqlalchemy.orm import Session
from sqlalchemy import asc, desc, func
from fastapi import APIRouter, Depends, HTTPException, Query, Request

router = APIRouter()

@router.get(
    "/events",
    response_model=UpcomingEventListResponse,
    summary="Retrieve a paginated list of all events, annotated with status",
)
def get_all_events(
    request: Request,
    *,
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Filter by description"),
    sort_by: str = Query("date", regex="^(id|date|created_at)$", description="Field to sort by"),
    order: str = Query("asc", regex="^(asc|desc)$", description="Sort direction"),
) -> UpcomingEventListResponse:
    """
    Retrieve all events with:
    - total count of records
    - current page and page_size
    - next_page and prev_page full URLs
    - each event includes a `status` ("Ended", "Happening", "Upcoming")
    """
    # 1) Count total events
    total = db.query(func.count(UpComingEvents.id)).scalar()

    # 2) Build base query (no date filtering)
    query = db.query(UpComingEvents)

    # 3) Optional search by description
    if search:
        term = f"%{search.strip()}%"
        query = query.filter(UpComingEvents.description.ilike(term))

    # 4) Apply ordering
    direction = asc if order == "asc" else desc
    column = getattr(UpComingEvents, sort_by)
    query = query.order_by(direction(column))

    # 5) Pagination
    offset = (page - 1) * page_size
    raw_items = query.offset(offset).limit(page_size).all()

    if not raw_items and page != 1:
        raise HTTPException(status_code=404, detail="Page out of range")

    # 6) Annotate and build schema instances manually
    today = date.today()
    items = []
    for ev in raw_items:
        if ev.date == today:
            status = "Happening"
        elif ev.date > today:
            status = "Upcoming"
        else:
            status = "Ended"

        items.append(UpcomingEventSchema(
            id=ev.id,
            photo=ev.photo,
            date=ev.date,
            description=ev.description,
            status=status,
        ))

    # 7) Build navigation URLs
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
