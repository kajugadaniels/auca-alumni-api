import os
import datetime
from io import BytesIO
from typing import Optional

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
    UploadFile,
    File,
    Form,
    Request,
    Query,
)
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import asc, desc, func
from PIL import Image, UnidentifiedImageError

from database import get_db
from models import Sliders
from schemas.sliders import CreateSliderSchema, SliderSchema, SliderListResponse
from routers.auth import get_current_user

router = APIRouter(
    prefix="/sliders",
    tags=["sliders"],
    dependencies=[Depends(get_current_user)],
)

# Ensure uploads directory exists
UPLOAD_DIR = os.path.join(os.getcwd(), "uploads", "sliders")
os.makedirs(UPLOAD_DIR, exist_ok=True)


# ------------------------------------------------------------------------
# GET /sliders: list all sliders with pagination
# ------------------------------------------------------------------------
@router.get(
    "/",
    response_model=SliderListResponse,
    summary="Retrieve a paginated list of sliders with full metadata and image URLs",
)
def list_sliders(
    request: Request,
    *,
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    sort_by: str = Query(
        "created_at",
        regex="^(id|created_at)$",
        description="Field to sort by; defaults to `created_at`",
    ),
    order: str = Query(
        "desc",
        regex="^(asc|desc)$",
        description="Sort direction; defaults to descending (latest first)",
    ),
) -> SliderListResponse:
    """
    Retrieve all slider entries with:
    - total count
    - pagination metadata
    - full URLs for the `photo` field
    """
    # 1) Total count
    total = db.query(func.count(Sliders.id)).scalar()

    # 2) Base query
    query = db.query(Sliders)

    # 3) Ordering
    direction = asc if order == "asc" else desc
    column = getattr(Sliders, sort_by)
    query = query.order_by(direction(column))

    # 4) Pagination
    offset = (page - 1) * page_size
    raw_items = query.offset(offset).limit(page_size).all()
    if not raw_items and page != 1:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Page out of range")

    # 5) Build items with full photo URLs
    base = str(request.base_url).rstrip("/")
    items = [
        SliderSchema(
            id=slide.id,
            photo=f"{base}{slide.photo}",
            description=slide.description,
            created_at=slide.created_at,
            updated_at=slide.updated_at,
        )
        for slide in raw_items
    ]

    # 6) Navigation URLs
    def make_url(p: int) -> str:
        return str(request.url.include_query_params(page=p, page_size=page_size))

    prev_page = make_url(page - 1) if page > 1 else None
    next_page = make_url(page + 1) if offset + len(items) < total else None

    return SliderListResponse(
        total=total,
        page=page,
        page_size=page_size,
        next_page=next_page,
        prev_page=prev_page,
        items=items,
    )

# ------------------------------------------------------------------------
# POST /sliders/add: create a new slider with image upload and auto-crop
# ------------------------------------------------------------------------
@router.post(
    "/add",
    status_code=status.HTTP_201_CREATED,
    summary="Create a new slider with image upload and auto-crop",
)
async def add_slider(
    request: Request,
    description: str = Form(..., description="Slider description"),
    photo: UploadFile = File(..., description="Image file for the slider"),
    db: Session = Depends(get_db),
):
    """
    Creates a new slider:
    - Validates via CreateSliderSchema
    - Saves and crops image (1270×720) in‐memory
    - Persists and returns full metadata
    """
    # 1) Validate metadata
    data = CreateSliderSchema(description=description)

    # 2) Build filename
    slug = "".join(c for c in data.description.lower().replace(" ", "_") if c.isalnum() or c == "_")
    timestamp = datetime.datetime.utcnow().strftime("%Y%m%d%H%M%S")
    ext = os.path.splitext(photo.filename)[1] or ".jpg"
    filename = f"{slug}_{timestamp}{ext}"
    filepath = os.path.join(UPLOAD_DIR, filename)

    # 3) Read & validate image in-memory
    contents = await photo.read()
    buffer = BytesIO(contents)
    try:
        img = Image.open(buffer)
        img = img.convert("RGB")
        img = img.resize((1270, 720), Image.LANCZOS)
    except UnidentifiedImageError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "invalid_image",
                "message": "Uploaded file is not a valid image."
            },
        )

    # 4) Save the processed image to disk
    try:
        img.save(filepath, quality=85)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "save_failed",
                "message": "Failed to save image on the server."
            },
        )

    # 5) Persist record
    new_slide = Sliders(
        photo=f"/uploads/sliders/{filename}",
        description=data.description,
    )
    db.add(new_slide)
    db.commit()
    db.refresh(new_slide)

    # 6) Build full photo URL
    base = str(request.base_url).rstrip("/")
    photo_url = f"{base}{new_slide.photo}"

    # 7) Return success JSON
    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={
            "status": "success",
            "message": "Slider created successfully.",
            "slider": {
                "id": new_slide.id,
                "photo": photo_url,
                "description": new_slide.description,
                "created_at": new_slide.created_at.isoformat(),
                "updated_at": new_slide.updated_at.isoformat(),
            },
        },
    )
