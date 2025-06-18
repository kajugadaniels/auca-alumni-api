import os
import datetime
from typing import Optional
from PIL import Image

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
    UploadFile,
    File,
    Form,
    Request,
)
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import func

from database import get_db
from models import LatestNews
from schemas.news import CreateNewsSchema, LatestNewsSchema
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

# ------------------------------------------------------------------------
# POST /news/add: create a new news item with image upload
# ------------------------------------------------------------------------
@router.post(
    "/news/add",
    status_code=status.HTTP_201_CREATED,
    summary="Create a new latest news item with image upload and auto-crop",
)
async def add_news(
    title: str = Form(..., min_length=5, description="News title"),
    date: datetime.date = Form(..., description="Date of the news"),
    description: str = Form(..., min_length=10, description="News description"),
    photo: UploadFile = File(..., description="Image file for the news"),
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Creates a new news item:
    - Validates no future dates
    - Prevents duplicate title+date
    - Saves and crops image (1270×720)
    - Returns the newly created record with full image URL
    """
    # 1) Validate metadata via Pydantic
    data = CreateNewsSchema(title=title, date=date, description=description)

    # 2) Prevent duplicates
    if (
        db.query(LatestNews)
        .filter(
            LatestNews.title == data.title.strip(),
            LatestNews.date == data.date,
        )
        .first()
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "news_exists",
                "message": f"A news item titled '{data.title}' on {data.date} already exists."
            },
        )

    # 3) Build filename
    slug = "".join(
        c for c in data.title.lower().replace(" ", "_")
        if c.isalnum() or c == "_"
    )
    date_str = data.date.strftime("%Y%m%d")
    ext = os.path.splitext(photo.filename)[1] or ".jpg"
    filename = f"{slug}_{date_str}{ext}"
    filepath = os.path.join(NEWS_UPLOAD_DIR, filename)

    # 4) Save and crop image
    contents = await photo.read()
    with open(filepath, "wb") as f:
        f.write(contents)

    try:
        img = Image.open(filepath)
        img = img.convert("RGB")
        img = img.resize((1270, 720), Image.LANCZOS)
        img.save(filepath, quality=85)
    except Exception:
        os.remove(filepath)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "invalid_image",
                "message": "Uploaded file is not a valid image."
            },
        )

    # 5) Persist record
    new_news = LatestNews(
        title=data.title.strip(),
        date=data.date,
        description=data.description.strip(),
        photo=f"/uploads/news/{filename}",
    )
    db.add(new_news)
    db.commit()
    db.refresh(new_news)

    # 6) Build full photo URL
    base = str(request.base_url).rstrip("/")
    full_photo_url = f"{base}{new_news.photo}"

    # 7) Return success JSON
    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={
            "status": "success",
            "message": "News item created successfully.",
            "news": {
                "id": new_news.id,
                "title": new_news.title,
                "date": str(new_news.date),
                "description": new_news.description,
                "photo": full_photo_url,
                "created_at": new_news.created_at.isoformat(),
                "updated_at": new_news.updated_at.isoformat(),
            },
        },
    )