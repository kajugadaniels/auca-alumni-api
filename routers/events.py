from models import *
from datetime import date
from schemas.event import *
from database import get_db
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import asc, desc, func
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Body, status

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

@router.post(
    "/event/add",
    response_model=UpcomingEventSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new event",
)
def create_event(
    data: UpcomingEventCreateSchema = Body(...),
    db: Session = Depends(get_db),
) -> JSONResponse:
    """
    Create a new event record.
    Returns 201 with the created event on success,
    or 400 with error details on failure.
    """
    try:
        new_event = UpComingEvents(
            photo=data.photo.strip(),
            date=data.date,
            description=data.description.strip(),
        )
        db.add(new_event)
        db.commit()
        db.refresh(new_event)

    except IntegrityError as e:
        db.rollback()
        # Could inspect e.orig for specific constraint, but generic message:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "status": "error",
                "message": "Failed to create event due to database constraint.",
                "details": str(e.orig),
            },
        )

    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={
            "status": "success",
            "message": "Event created successfully.",
            "event": {
                "id": new_event.id,
                "photo": new_event.photo,
                "date": new_event.date.isoformat(),
                "description": new_event.description,
            },
        },
    )