import os
import shutil
import datetime
from typing import Optional
from uuid import uuid4
from PIL import Image

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Request,
    status,
    File,
    UploadFile,
    Form,
)
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import asc, desc, func

from database import get_db
from models import UpComingEvents
from schemas.event import (
    CreateEventSchema,
    UpcomingEventListResponse,
    UpcomingEventSchema,
)
from routers.auth import get_current_user

router = APIRouter(
    dependencies=[Depends(get_current_user)],
    # prefix="/api",
    tags=["events"],
)

# Directory for event uploads
UPLOAD_DIR = os.path.join(os.getcwd(), "uploads", "events")
os.makedirs(UPLOAD_DIR, exist_ok=True)


# ------------------------------------------------------------------------
# GET /events: list all events with status
# ------------------------------------------------------------------------
@router.get(
    "/events",
    response_model=UpcomingEventListResponse,
    summary="Retrieve a paginated list of all events, annotated with status",
)
def getEvents(
    request: Request,
    *,
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Filter by description"),
    sort_by: str = Query(
        "created_at", regex="^(id|date|created_at)$",
        description="Field to sort by; defaults to creation timestamp"
    ),
    order: str = Query(
        "desc", regex="^(asc|desc)$",
        description="Sort direction; defaults to descending (latest first)"
    ),
) -> UpcomingEventListResponse:
    """
    Retrieve all events with created/updated timestamps and a computed `status`.
    """
    total = db.query(func.count(UpComingEvents.id)).scalar()
    query = db.query(UpComingEvents)

    if search:
        term = f"%{search.strip()}%"
        query = query.filter(UpComingEvents.description.ilike(term))

    direction = asc if order == "asc" else desc
    column = getattr(UpComingEvents, sort_by)
    query = query.order_by(direction(column))

    offset = (page - 1) * page_size
    raw_items = query.offset(offset).limit(page_size).all()
    if not raw_items and page != 1:
        raise HTTPException(status_code=404, detail="Page out of range")

    today = datetime.date.today()
    items = []
    for ev in raw_items:
        if ev.date == today:
            status_label = "Happening"
        elif ev.date > today:
            status_label = "Upcoming"
        else:
            status_label = "Ended"

        # Build full photo URL
        photo_url = request.url_for("uploads") + ev.photo.lstrip("/")

        items.append(
            UpcomingEventSchema(
                id=ev.id,
                photo=photo_url,
                date=ev.date,
                description=ev.description,
                status=status_label,
                created_at=ev.created_at,
                updated_at=ev.updated_at,
            )
        )

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
# POST /events/add: create a new event with image upload
# ------------------------------------------------------------------------
@router.post(
    "/event/add",
    status_code=status.HTTP_201_CREATED,
    summary="Create a new event with local image upload and auto‐crop",
)
async def addEvent(
    event_date: datetime.date = Form(...),
    description: str = Form(..., min_length=10),
    photo: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    Accepts:
    - `event_date` (must not be in the past)
    - `description`
    - `photo` (image file)

    Saves the cropped image (1270×720) under /uploads/events,
    names it `{slug}_{YYYYMMDD}{ext}`, and persists the record.
    """
    # Validate date
    if event_date < datetime.date.today():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "date_in_past", "message": "Event date cannot be in the past."},
        )

    # Prevent exact duplicates
    if (
        db.query(UpComingEvents)
        .filter(
            UpComingEvents.date == event_date,
            UpComingEvents.description == description.strip(),
        )
        .first()
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "event_exists", "message": "An identical event already exists."},
        )

    # Determine filename
    slug = "".join(e for e in description.lower().replace(" ", "_") if e.isalnum() or e == "_")
    date_str = event_date.strftime("%Y%m%d")
    ext = os.path.splitext(photo.filename)[1] or ".jpg"
    filename = f"{slug}_{date_str}{ext}"
    filepath = os.path.join(UPLOAD_DIR, filename)

    # Save and crop
    with open(filepath, "wb") as out_file:
        contents = await photo.read()
        out_file.write(contents)

    try:
        img = Image.open(filepath)
        img = img.convert("RGB")
        img = img.resize((1270, 720), Image.LANCZOS)
        img.save(filepath, quality=85)
    except Exception:
        # clean up on failure
        os.remove(filepath)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "invalid_image", "message": "Uploaded file is not a valid image."},
        )

    # Persist
    new_event = UpComingEvents(
        photo=f"/uploads/events/{filename}",
        date=event_date,
        description=description.strip(),
    )
    db.add(new_event)
    db.commit()
    db.refresh(new_event)

    # Compute status
    today = datetime.date.today()
    if event_date == today:
        status_label = "Happening"
    elif event_date > today:
        status_label = "Upcoming"
    else:
        status_label = "Ended"

    created = new_event.created_at or datetime.datetime.utcnow()
    updated = new_event.updated_at or created

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
                "created_at": created.isoformat(),
                "updated_at": updated.isoformat(),
            },
        },
    )

# ------------------------------------------------------------------------
# GET /events/{event_id}: retrieve a specific event by ID
# ------------------------------------------------------------------------
@router.get(
    "/event/{event_id}",
    response_model=UpcomingEventSchema,
    summary="Retrieve detailed information for a single event by ID",
)
def getEventDetails(
    event_id: int,
    db: Session = Depends(get_db),
):
    """
    Fetch a single event record by its ID.
    Returns 404 if not found, otherwise all fields plus computed status.
    """
    event = db.query(UpComingEvents).get(event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "event_not_found", "message": f"No event found with ID {event_id}."},
        )

    # Compute status
    today = datetime.date.today()
    if event.date == today:
        status_label = "Happening"
    elif event.date > today:
        status_label = "Upcoming"
    else:
        status_label = "Ended"

    # Build and return schema
    return UpcomingEventSchema(
        id=event.id,
        photo=event.photo,
        date=event.date,
        description=event.description,
        status=status_label,
        created_at=event.created_at,
        updated_at=event.updated_at,
    )

# ------------------------------------------------------------------------
# PUT /events/{event_id}: update an existing event
# ------------------------------------------------------------------------
@router.put(
    "/event/{event_id}/update/",
    response_model=UpcomingEventSchema,
    summary="Update an existing event by ID",
)
async def updateEvent(
    event_id: int,
    event_date: datetime.date = Form(..., description="New date for the event"),
    description: str = Form(..., min_length=10, description="New description"),
    photo: UploadFile | None = File(None, description="New image file (optional)"),
    db: Session = Depends(get_db),
):
    """
    Update the event's date, description, and optionally replace its photo.
    - Validates that the new date is not in the past.
    - Prevents duplicate date+description combos.
    - If a new photo is provided, replaces, renames, and crops it.
    """
    # 1) Fetch existing
    event = db.query(UpComingEvents).get(event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "event_not_found", "message": f"No event found with ID {event_id}."},
        )

    # 2) Validate date
    if event_date < datetime.date.today():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "date_in_past", "message": "Event date cannot be in the past."},
        )

    # 3) Prevent duplicate on new date & description
    duplicate = (
        db.query(UpComingEvents)
        .filter(
            UpComingEvents.id != event_id,
            UpComingEvents.date == event_date,
            UpComingEvents.description == description.strip(),
        )
        .first()
    )
    if duplicate:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "event_exists", "message": "Another event with this date and description exists."},
        )

    # 4) Update fields
    event.date = event_date
    event.description = description.strip()

    # 5) Handle new photo if provided
    if photo:
        # Remove old file
        old_path = os.path.join(os.getcwd(), event.photo.lstrip("/"))
        if os.path.isfile(old_path):
            os.remove(old_path)

        # Build new filename
        slug = "".join(
            c for c in description.lower().replace(" ", "_") if c.isalnum() or c == "_"
        )
        date_str = event_date.strftime("%Y%m%d")
        ext = os.path.splitext(photo.filename)[1] or ".jpg"
        filename = f"{slug}_{date_str}{ext}"
        filepath = os.path.join(UPLOAD_DIR, filename)

        # Save upload
        with open(filepath, "wb") as out_file:
            contents = await photo.read()
            out_file.write(contents)

        # Crop & resize
        try:
            img = Image.open(filepath)
            img = img.convert("RGB")
            img = img.resize((1270, 720), Image.LANCZOS)
            img.save(filepath, quality=85)
        except Exception:
            os.remove(filepath)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "invalid_image", "message": "Uploaded file is not a valid image."},
            )

        event.photo = f"/uploads/events/{filename}"

    # 6) Commit changes
    db.add(event)
    db.commit()
    db.refresh(event)

    # 7) Compute status
    today = datetime.date.today()
    if event.date == today:
        status_label = "Happening"
    elif event.date > today:
        status_label = "Upcoming"
    else:
        status_label = "Ended"

    # 8) Respond with updated record
    return UpcomingEventSchema(
        id=event.id,
        photo=event.photo,
        date=event.date,
        description=event.description,
        status=status_label,
        created_at=event.created_at,
        updated_at=event.updated_at,
    )

# ------------------------------------------------------------------------
# DELETE /events/{event_id}: delete an event and its image
# ------------------------------------------------------------------------
@router.delete(
    "/event/{event_id}/delete",
    status_code=status.HTTP_200_OK,
    summary="Delete a specific event and its associated image",
)
def deleteEvent(
    event_id: int,
    db: Session = Depends(get_db),
):
    """
    Deletes the event record identified by `event_id`.
    Also removes the corresponding image file from disk.
    Returns a success message, or 404 if not found.
    """
    # 1) Fetch the event
    event = db.query(UpComingEvents).get(event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "event_not_found", "message": f"No event found with ID {event_id}."},
        )

    # 2) Delete the image file
    image_path = os.path.join(os.getcwd(), event.photo.lstrip("/"))
    if os.path.isfile(image_path):
        try:
            os.remove(image_path)
        except Exception:
            # Log the error in real-world apps
            pass

    # 3) Delete the database record
    db.delete(event)
    db.commit()

    # 4) Return success JSON
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": "success",
            "message": f"Event with ID {event_id} has been deleted successfully."
        },
    )