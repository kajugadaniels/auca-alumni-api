"""
Protected CRUD router for UpComingEvents. Requires authentication.
Handles upload, retrieval, update, detail view, and deletion.
Image uploads are cropped to portrait via Pillow.
"""
import io
import os
from PIL import Image
from routers.auth import *
from schemas.event import *
from database import get_db
from models import UpComingEvents
from sqlalchemy.orm import Session
from fastapi.responses import JSONResponse
from utils.security import decode_access_token
from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, status

router = APIRouter()

IMAGE_DIR = "./uploads/events"
os.makedirs(IMAGE_DIR, exist_ok=True)

@router.get(
    "/events",
    response_model=list[EventResponse],
    summary="List all upcoming events",
)
def list_events(
    current=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve all events."""
    events = db.query(UpComingEvents).order_by(UpComingEvents.date).all()
    return events

@router.post(
    "/event/add",
    response_model=EventResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new upcoming event",
)
def create_event(
    file: UploadFile = File(..., description="Event image to upload"),
    date: date = Depends(),
    description: str = Depends(),
    current=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Uploads an image, crops/resizes it to exactly 1270×720, saves locally,
    and creates an event record.
    """
    # 1) Validate image
    try:
        raw = file.file.read()
        image = Image.open(io.BytesIO(raw))
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "invalid_image",
                "message": "Uploaded file is not a valid image."
            },
        )

    # 2) Crop to 16:9 and resize to 1270×720
    try:
        width, height = image.size
        target_ratio = 1270 / 720
        current_ratio = width / height

        if current_ratio > target_ratio:
            # image is too wide → crop width
            new_width = int(height * target_ratio)
            left = (width - new_width) // 2
            box = (left, 0, left + new_width, height)
        else:
            # image is too tall → crop height
            new_height = int(width / target_ratio)
            top = (height - new_height) // 2
            box = (0, top, width, top + new_height)

        cropped = image.crop(box)
        resized = cropped.resize((1270, 720))
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "processing_error",
                "message": "Failed to crop/resize the image."
            },
        )

    # 3) Save processed image
    try:
        ts = int(time.time())
        fname = f"event_{ts}_{file.filename}".replace(" ", "_")
        path = os.path.join(IMAGE_DIR, fname)
        resized.save(path)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "save_error",
                "message": "Failed to save the processed image."
            },
        )

    # 4) Create DB record
    try:
        event = UpComingEvents(photo=path, date=date, description=description)
        db.add(event)
        db.commit()
        db.refresh(event)
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "db_error",
                "message": "Failed to write event to the database."
            },
        )

    # 5) Return detailed success JSON
    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={
            "status": "success",
            "message": "Event created successfully.",
            "event": {
                "id": event.id,
                "photo": event.photo,
                "date": str(event.date),
                "description": event.description,
            },
        },
    )

@router.get(
    "/event/{event_id}",
    response_model=EventResponse,
    summary="Get details of a specific event",
)
def get_event(
    event_id: int,
    current=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve event by ID."""
    event = db.query(UpComingEvents).get(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found.")
    return event

@router.put(
    "/event/{event_id}/update",
    response_model=EventResponse,
    summary="Update an existing event",
)
def update_event(
    event_id: int,
    data: EventUpdate,
    file: UploadFile | None = File(None),
    current=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update event fields and optionally replace image.
    Uploaded image is cropped to portrait.
    """
    event = db.query(UpComingEvents).get(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found.")
    # Process new image if provided
    if file:
        image = Image.open(io.BytesIO(file.file.read()))
        width, height = image.size
        if width > height:
            left = (width - height) / 2
            right = left + height
            cropped = image.crop((left, 0, right, height))
        else:
            cropped = image
        filename = f"event_{int(io.time.time())}_{file.filename}"
        path = os.path.join(IMAGE_DIR, filename)
        cropped.save(path)
        event.photo = path
    # Update other fields
    if data.date:
        event.date = data.date
    if data.description:
        event.description = data.description
    db.commit()
    db.refresh(event)
    return event

@router.delete(
    "/event/{event_id}/delete",
    response_model=None,
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an event",
)
def delete_event(
    event_id: int,
    current=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete an event by ID."""
    event = db.query(UpComingEvents).get(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found.")
    db.delete(event)
    db.commit()
    return JSONResponse(status_code=status.HTTP_204_NO_CONTENT, content=None)