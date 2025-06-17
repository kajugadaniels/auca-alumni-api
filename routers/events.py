import datetime
from models import *
from schemas.event import *
from database import get_db
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import asc, desc, func
from fastapi.responses import JSONResponse
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

router = APIRouter()

# ------------------------------------------------------------------------
# GET /events: list all events with status
# ------------------------------------------------------------------------
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
    sort_by: str = Query(
        "date", regex="^(id|date|created_at)$", description="Field to sort by"
    ),
    order: str = Query("asc", regex="^(asc|desc)$", description="Sort direction"),
) -> UpcomingEventListResponse:
    """
    Retrieve all events with:
    - total count of records
    - current page and page_size
    - next_page and prev_page full URLs
    - each event includes a `status` ("Ended", "Happening", "Upcoming")
    """
    # 1) Total count
    total = db.query(func.count(UpComingEvents.id)).scalar()

    # 2) Base query
    query = db.query(UpComingEvents)

    # 3) Search filter
    if search:
        term = f"%{search.strip()}%"
        query = query.filter(UpComingEvents.description.ilike(term))

    # 4) Ordering
    direction = asc if order == "asc" else desc
    column = getattr(UpComingEvents, sort_by)
    query = query.order_by(direction(column))

    # 5) Pagination
    offset = (page - 1) * page_size
    raw_items = query.offset(offset).limit(page_size).all()
    if not raw_items and page != 1:
        raise HTTPException(status_code=404, detail="Page out of range")

    # 6) Annotate status
    today = datetime.date.today()
    items = []
    for ev in raw_items:
        if ev.date == today:
            status_label = "Happening"
        elif ev.date > today:
            status_label = "Upcoming"
        else:
            status_label = "Ended"

        items.append(
            UpcomingEventSchema(
                id=ev.id,
                photo=ev.photo,
                date=ev.date,
                description=ev.description,
                status=status_label,
            )
        )

    # 7) Navigation URLs
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

# ------------------------------------------------------------------------
# POST /events: add a new event
# ------------------------------------------------------------------------
@router.post(
    "/events",
    status_code=status.HTTP_201_CREATED,
    summary="Create a new event",
)
def create_event(
    data: CreateEventSchema,
    db: Session = Depends(get_db),
):
    """
    Create and persist a new upcoming event.
    Returns detailed success or error messages.
    """
    # 1) Prevent duplicate on same date & description
    existing = (
        db.query(UpComingEvents)
        .filter(
            UpComingEvents.date == data.event_date,
            UpComingEvents.description == data.description.strip(),
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "event_exists",
                "message": f"An event on {data.event_date} with the same description already exists.",
            },
        )

    # 2) Create and save
    new_event = UpComingEvents(
        photo=str(data.photo),
        date=data.event_date,
        description=data.description.strip(),
    )
    db.add(new_event)
    db.commit()
    db.refresh(new_event)

    # 3) Compute status for the created event
    today = datetime.date.today()
    if new_event.date == today:
        status_label = "Happening"
    elif new_event.date > today:
        status_label = "Upcoming"
    else:
        status_label = "Ended"

    # 4) Return success JSON
    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={
            "status": "success",
            "message": "Event created successfully.",
            "event": {
                "id": new_event.id,
                "photo": new_event.photo,
                "date": str(new_event.date),
                "description": new_event.description,
                "status": status_label,
            },
        },
    )
