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
    Query,
    Request,
)
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from PIL import Image, UnidentifiedImageError
from sqlalchemy import asc, desc, func

from database import get_db
from models import SocialActivities
from schemas.social_activities import CreateSocialActivitySchema, SocialActivitySchema, SocialActivityListResponse
from routers.auth import get_current_user

router = APIRouter(
    prefix="/social-activities",
    tags=["social-activities"],
    dependencies=[Depends(get_current_user)],
)

# Ensure uploads directory exists (for photo storage)
UPLOAD_DIR = os.path.join(os.getcwd(), "uploads", "social_activities")
os.makedirs(UPLOAD_DIR, exist_ok=True)


# ------------------------------------------------------------------------
# GET /social-activities: list all social activities with pagination
# ------------------------------------------------------------------------
@router.get(
    "/",
    response_model=SocialActivityListResponse,
    summary="Retrieve a paginated list of social activities with full metadata and image URLs",
)
def list_social_activities(
    request: Request,
    *,
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Filter by title or description"),
    sort_by: str = Query(
        "created_at",
        regex="^(id|date|created_at)$",
        description="Field to sort by; defaults to `date`",
    ),
    order: str = Query(
        "desc",
        regex="^(asc|desc)$",
        description="Sort direction; defaults to ascending (earliest first)",
    ),
) -> SocialActivityListResponse:
    """
    Retrieve all social activities with:
    - total count
    - pagination metadata
    - full URLs for the `photo` field
    """
    # 1) Total count
    total = db.query(func.count(SocialActivities.id)).scalar()

    # 2) Base query
    query = db.query(SocialActivities)
    if search:
        term = f"%{search.strip()}%"
        query = query.filter(
            SocialActivities.title.ilike(term) | SocialActivities.description.ilike(term)
        )

    # 3) Ordering
    direction = asc if order == "asc" else desc
    column = getattr(SocialActivities, sort_by)
    query = query.order_by(direction(column))

    # 4) Pagination
    offset = (page - 1) * page_size
    raw_items = query.offset(offset).limit(page_size).all()
    if not raw_items and page != 1:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Page out of range")

    # 5) Build items with full photo URLs
    base = str(request.base_url).rstrip("/")
    items = []
    for act in raw_items:
        photo_url = f"{base}{act.photo}"
        items.append(
            SocialActivitySchema(
                id=act.id,
                photo=photo_url,
                title=act.title,
                description=act.description,
                date=act.date,
                created_at=act.created_at,
                updated_at=act.updated_at,
            )
        )

    # 6) Navigation URLs
    def make_url(p: int) -> str:
        return str(request.url.include_query_params(page=p, page_size=page_size))

    prev_page = make_url(page - 1) if page > 1 else None
    next_page = make_url(page + 1) if offset + len(items) < total else None

    return SocialActivityListResponse(
        total=total,
        page=page,
        page_size=page_size,
        next_page=next_page,
        prev_page=prev_page,
        items=items,
    )

# ------------------------------------------------------------------------
# POST /social-activities/add: create a new social activity
# ------------------------------------------------------------------------
@router.post(
    "/add",
    status_code=status.HTTP_201_CREATED,
    summary="Create a new social activity with image upload and auto-crop",
)
async def add_social_activity(
    request: Request,
    title: str = Form(..., description="Activity title"),
    description: str = Form(..., description="Activity description"),
    date: datetime.date = Form(..., description="Date of the activity"),
    photo: UploadFile = File(..., description="Image file for the activity"),
    db: Session = Depends(get_db),
):
    """
    Creates a new social activity:
    - Validates via CreateSocialActivitySchema
    - Prevents duplicate title+date
    - Validates and crops image (1270×720) in‐memory
    - Persists and returns full metadata
    """
    # 1) Validate metadata
    data = CreateSocialActivitySchema(title=title, description=description, date=date)

    # 2) Duplicate check
    if (
        db.query(SocialActivities)
        .filter(
            SocialActivities.title == data.title,
            SocialActivities.date == data.date,
        )
        .first()
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "activity_exists",
                "message": f"An activity titled '{data.title}' on {data.date} already exists."
            },
        )

    # 3) Build filename
    slug = "".join(c for c in data.title.lower().replace(" ", "_") if c.isalnum() or c == "_")
    date_str = data.date.strftime("%Y%m%d")
    ext = os.path.splitext(photo.filename)[1] or ".jpg"
    filename = f"{slug}_{date_str}{ext}"
    filepath = os.path.join(UPLOAD_DIR, filename)

    # 4) Read & validate image in-memory
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

    # 5) Save the processed image to disk
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

    # 6) Persist record
    new_act = SocialActivities(
        title=data.title,
        description=data.description,
        date=data.date,
        photo=f"/uploads/social_activities/{filename}",
    )
    db.add(new_act)
    db.commit()
    db.refresh(new_act)

    # 7) Build full photo URL
    base = str(request.base_url).rstrip("/")
    photo_url = f"{base}{new_act.photo}"

    # 8) Return success JSON
    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={
            "status": "success",
            "message": "Social activity created successfully.",
            "activity": {
                "id": new_act.id,
                "title": new_act.title,
                "description": new_act.description,
                "date": str(new_act.date),
                "photo": photo_url,
                "created_at": new_act.created_at.isoformat(),
                "updated_at": new_act.updated_at.isoformat(),
            },
        },
    )

@router.get(
    "/{activity_id}",
    response_model=SocialActivitySchema,
    summary="Retrieve detailed information for a single social activity by ID",
)
def get_social_activity(
    activity_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Fetch a single SocialActivities record by its ID.
    Returns 404 if not found, otherwise all fields plus full image URL.
    """
    # 1) Load the record
    activity = db.query(SocialActivities).get(activity_id)
    if not activity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "activity_not_found",
                "message": f"No social activity found with ID {activity_id}."
            },
        )

    # 2) Build full photo URL
    base = str(request.base_url).rstrip("/")
    photo_url = f"{base}{activity.photo}"

    # 3) Return as schema
    return SocialActivitySchema(
        id=activity.id,
        photo=photo_url,
        title=activity.title,
        description=activity.description,
        date=activity.date,
        created_at=activity.created_at,
        updated_at=activity.updated_at,
    )

@router.put(
    "/{activity_id}/update",
    response_model=SocialActivitySchema,
    summary="Update an existing social activity by ID",
)
async def update_social_activity(
    activity_id: int,
    request: Request,
    title: str = Form(..., min_length=5, description="Updated activity title"),
    description: str = Form(..., min_length=10, description="Updated activity description"),
    date: datetime.date = Form(..., description="Updated date of the activity"),
    photo: Optional[UploadFile] = File(None, description="New image file (optional)"),
    db: Session = Depends(get_db),
):
    """
    Updates a social activity:
    - Validates via CreateSocialActivitySchema
    - Prevents duplicate title+date on other records
    - Optionally replaces, renames, and crops the image to 1270×720 in‐memory
    """
    # 1) Fetch existing
    activity = db.query(SocialActivities).get(activity_id)
    if not activity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "activity_not_found",
                "message": f"No social activity found with ID {activity_id}."
            },
        )

    # 2) Validate inputs
    data = CreateSocialActivitySchema(title=title, description=description, date=date)

    # 3) Prevent duplicate on other records
    dup = (
        db.query(SocialActivities)
        .filter(
            SocialActivities.id != activity_id,
            SocialActivities.title == data.title,
            SocialActivities.date == data.date,
        )
        .first()
    )
    if dup:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "activity_exists",
                "message": f"Another activity titled '{data.title}' on {data.date} already exists."
            },
        )

    # 4) Apply metadata updates
    activity.title = data.title
    activity.description = data.description
    activity.date = data.date

    # 5) Handle optional image replacement
    if photo:
        # 5a) Remove old file
        old_path = os.path.join(os.getcwd(), activity.photo.lstrip("/"))
        if os.path.isfile(old_path):
            try:
                os.remove(old_path)
            except Exception:
                pass  # log in production

        # 5b) Build new filename
        slug = "".join(c for c in data.title.lower().replace(" ", "_") if c.isalnum() or c == "_")
        date_str = date.strftime("%Y%m%d")
        ext = os.path.splitext(photo.filename)[1] or ".jpg"
        filename = f"{slug}_{date_str}{ext}"
        filepath = os.path.join(UPLOAD_DIR, filename)

        # 5c) Read & validate in-memory
        contents = await photo.read()
        buf = BytesIO(contents)
        try:
            img = Image.open(buf)
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

        # 5d) Save to disk
        try:
            img.save(filepath, quality=85)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"error": "save_failed", "message": "Failed to save image on server."},
            )

        activity.photo = f"/uploads/social_activities/{filename}"

    # 6) Commit changes
    db.add(activity)
    db.commit()
    db.refresh(activity)

    # 7) Build full URL
    base = str(request.base_url).rstrip("/")
    photo_url = f"{base}{activity.photo}"

    return SocialActivitySchema(
        id=activity.id,
        photo=photo_url,
        title=activity.title,
        description=activity.description,
        date=activity.date,
        created_at=activity.created_at,
        updated_at=activity.updated_at,
    )

@router.delete(
    "/{activity_id}/delete",
    status_code=status.HTTP_200_OK,
    summary="Delete a specific social activity and its associated image",
)
def delete_social_activity(
    activity_id: int,
    db: Session = Depends(get_db),
):
    """
    Deletes the social activity record identified by `activity_id`.
    Also removes the corresponding image file from disk.
    Returns a success message, or 404 if not found.
    """
    # 1) Fetch the activity
    activity = db.query(SocialActivities).get(activity_id)
    if not activity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "activity_not_found",
                "message": f"No social activity found with ID {activity_id}."
            },
        )

    # 2) Delete the image file
    image_path = os.path.join(os.getcwd(), activity.photo.lstrip("/"))
    if os.path.isfile(image_path):
        try:
            os.remove(image_path)
        except Exception:
            # In production, log this error
            pass

    # 3) Delete the database record
    db.delete(activity)
    db.commit()

    # 4) Return success JSON
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": "success",
            "message": f"Social activity with ID {activity_id} has been deleted successfully."
        },
    )