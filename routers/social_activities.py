import os
import datetime
from typing import Optional

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Request,
    status,
)
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import asc, desc, func

from database import get_db
from models import SocialActivities
from schemas.social_activities import SocialActivitySchema, SocialActivityListResponse
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
        "date",
        regex="^(id|date|created_at)$",
        description="Field to sort by; defaults to `date`",
    ),
    order: str = Query(
        "asc",
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
