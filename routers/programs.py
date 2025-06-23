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
from models import Programs
from schemas.program import ProgramSchema, ProgramListResponse
from routers.auth import get_current_user

router = APIRouter(
    prefix="/programs",
    tags=["programs"],
    dependencies=[Depends(get_current_user)],
)

# Ensure uploads directory exists (if storing program images here)
PROGRAMS_UPLOAD_DIR = os.path.join(os.getcwd(), "uploads", "programs")
os.makedirs(PROGRAMS_UPLOAD_DIR, exist_ok=True)


# ------------------------------------------------------------------------
# GET /programs: list all programs with pagination, search, sorting
# ------------------------------------------------------------------------
@router.get(
    "/",
    response_model=ProgramListResponse,
    summary="Retrieve a paginated list of programs with metadata and image URLs",
)
def list_programs(
    request: Request,
    *,
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Filter by title or description"),
    sort_by: str = Query(
        "created_at",
        regex="^(id|title|created_at)$",
        description="Field to sort by; defaults to `created_at`",
    ),
    order: str = Query(
        "desc",
        regex="^(asc|desc)$",
        description="Sort direction; defaults to descending (latest first)",
    ),
) -> ProgramListResponse:
    """
    Retrieve all programs with:
    - total count of records
    - pagination metadata
    - full URLs for the `photo` field
    """
    # 1) Total count
    total = db.query(func.count(Programs.id)).scalar()

    # 2) Base query
    query = db.query(Programs)
    if search:
        term = f"%{search.strip()}%"
        query = query.filter(
            Programs.title.ilike(term) | Programs.description.ilike(term)
        )

    # 3) Ordering
    direction = asc if order == "asc" else desc
    column = getattr(Programs, sort_by)
    query = query.order_by(direction(column))

    # 4) Pagination
    offset = (page - 1) * page_size
    raw_items = query.offset(offset).limit(page_size).all()
    if not raw_items and page != 1:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Page out of range")

    # 5) Build items with full photo URLs
    base = str(request.base_url).rstrip("/")
    items = []
    for prog in raw_items:
        photo_url = f"{base}{prog.photo}"
        items.append(
            ProgramSchema(
                id=prog.id,
                title=prog.title,
                description=prog.description,
                photo=photo_url,
                created_at=prog.created_at,
                updated_at=prog.updated_at,
            )
        )

    # 6) Navigation URLs
    def make_url(p: int) -> str:
        return str(request.url.include_query_params(page=p, page_size=page_size))

    prev_page = make_url(page - 1) if page > 1 else None
    next_page = make_url(page + 1) if offset + len(items) < total else None

    return ProgramListResponse(
        total=total,
        page=page,
        page_size=page_size,
        next_page=next_page,
        prev_page=prev_page,
        items=items,
    )
