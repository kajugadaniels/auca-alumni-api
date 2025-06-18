import os
import datetime
from typing import Optional

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Request,
)
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import asc, desc, func

from database import get_db
from models import LatestNews
from schemas.news import LatestNewsSchema, LatestNewsListResponse
from routers.auth import get_current_user

router = APIRouter(
    # prefix="/news",
    tags=["news"],
    dependencies=[Depends(get_current_user)],
)

# Ensure uploads directory exists
NEWS_UPLOAD_DIR = os.path.join(os.getcwd(), "uploads", "news")
os.makedirs(NEWS_UPLOAD_DIR, exist_ok=True)


# ------------------------------------------------------------------------
# GET /news: list all news with pagination
# ------------------------------------------------------------------------
@router.get(
    "/news",
    response_model=LatestNewsListResponse,
    summary="Retrieve a paginated list of latest news items with full metadata and image URLs",
)
def list_news(
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
        description="Sort direction; defaults to descending (latest first)",
    ),
) -> LatestNewsListResponse:
    """
    Retrieve all news items with:
    - total count
    - pagination metadata
    - full URLs for the `photo` field
    """
    # 1) Total count
    total = db.query(func.count(LatestNews.id)).scalar()

    # 2) Base query
    query = db.query(LatestNews)
    if search:
        term = f"%{search.strip()}%"
        query = query.filter(
            LatestNews.title.ilike(term) | LatestNews.description.ilike(term)
        )

    # 3) Ordering
    direction = asc if order == "asc" else desc
    column = getattr(LatestNews, sort_by)
    query = query.order_by(direction(column))

    # 4) Pagination
    offset = (page - 1) * page_size
    raw_items = query.offset(offset).limit(page_size).all()
    if not raw_items and page != 1:
        raise HTTPException(status_code=404, detail="Page out of range")

    # 5) Build items with full photo URLs
    base = str(request.base_url).rstrip("/")
    items = []
    for news in raw_items:
        photo_url = f"{base}{news.photo}"
        items.append(
            LatestNewsSchema(
                id=news.id,
                title=news.title,
                date=news.date,
                description=news.description,
                photo=photo_url,
                created_at=news.created_at,
                updated_at=news.updated_at,
            )
        )

    # 6) Navigation URLs
    def make_url(p: int) -> str:
        return str(request.url.include_query_params(page=p, page_size=page_size))

    prev_page = make_url(page - 1) if page > 1 else None
    next_page = make_url(page + 1) if offset + len(items) < total else None

    return LatestNewsListResponse(
        total=total,
        page=page,
        page_size=page_size,
        next_page=next_page,
        prev_page=prev_page,
        items=items,
    )
