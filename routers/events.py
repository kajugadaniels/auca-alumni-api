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

@router.post(
    "/events",
    response_model=EventResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new upcoming event",
)
def create_event(
    file: UploadFile = File(..., description="Event image to upload"),
    date: str = Depends(),
    description: str = Depends(),
    current=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Uploads an image, crops it to portrait, saves locally, and creates an event record.
    """
    # Validate and process image
    try:
        image = Image.open(io.BytesIO(file.file.read()))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid image file.")
    # Crop to portrait (height >= width)
    width, height = image.size
    if width > height:
        left = (width - height) / 2
        right = left + height
        cropped = image.crop((left, 0, right, height))
    else:
        cropped = image
    # Save image
    filename = f"event_{int(io.time.time())}_{file.filename}"
    path = os.path.join(IMAGE_DIR, filename)
    cropped.save(path)
    # Create DB record
    event = UpComingEvents(photo=path, date=date, description=description)
    db.add(event)
    db.commit()
    db.refresh(event)
    return event