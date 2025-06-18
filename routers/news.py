import os
import datetime
from PIL import Image
from uuid import uuid4
from typing import Optional

from fastapi import (
    Form,
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Request,
    status,
    File,
    UploadFile,
)
from sqlalchemy import asc, desc, func
from sqlalchemy.orm import Session
from fastapi.responses import JSONResponse

from models import *
from database import get_db
from routers.auth import get_current_user
from schemas.news import CreateNewsSchema, NewsListResponse, NewsSchema

router = APIRouter(
    prefix="/news",
    tags=["news"],
    dependencies=[Depends(get_current_user)],
)

@router.get(
    "/",
    response_model=NewsListResponse,
    summary="Retrieve a paginated list of latest news with full image URLs",
)
def getNews(
    request: Request,
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Filter by title or description"),
    sort_by: str = Query(
        "created_at", regex="^(id|date|created_at)$", description="Field to sort by"
    ),
    order: str = Query("desc", regex="^(asc|desc)$", description="Sort direction"),
) -> NewsListResponse:
    """
    Retrieve news items:
    - total count
    - paginated list
    - next/prev page URLs
    - full URLs to images
    """
    # 1) Total count
    total = db.query(func.count(LatestNews.id)).scalar()

    # 2) Base query
    query = db.query(LatestNews)

    # 3) Search filter
    if search:
        term = f"%{search.strip()}%"
        query = query.filter(
            LatestNews.title.ilike(term) | LatestNews.description.ilike(term)
        )

    # 4) Ordering
    direction = asc if order == "asc" else desc
    column = getattr(LatestNews, sort_by)
    query = query.order_by(direction(column))

    # 5) Pagination
    offset = (page - 1) * page_size
    raw_items = query.offset(offset).limit(page_size).all()
    if not raw_items and page != 1:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Page out of range")

    # 6) Build response items
    items = []
    for news in raw_items:
        # full image URL
        photo_url = str(request.base_url).rstrip("/") + news.photo
        items.append(
            NewsSchema(
                id=news.id,
                title=news.title,
                date=news.date,
                description=news.description,
                photo=photo_url,
                created_at=news.created_at,
                updated_at=news.updated_at,
            )
        )

    # 7) Navigation URLs
    def make_url(p: int) -> str:
        return str(request.url.include_query_params(page=p, page_size=page_size))

    prev_page = make_url(page - 1) if page > 1 else None
    next_page = make_url(page + 1) if offset + len(items) < total else None

    return NewsListResponse(
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
    "/event/add",
    status_code=status.HTTP_201_CREATED,
    summary="Create a new latest news entry with image upload and auto-crop",
)
async def addNews(
    request: Request,
    title: str = Form(..., min_length=5, description="Headline of the news item"),
    date: datetime.date = Form(..., description="Publication date of the news"),
    description: str = Form(..., min_length=10, description="Full news description"),
    photo: UploadFile = File(..., description="Image file for the news item"),
    db: Session = Depends(get_db),
):
    """
    Accepts title, date, description, and photo;
    validates via CreateNewsSchema; saves & crops the image;
    persists the record; returns detailed response.
    """
    # 1) Validate input via Pydantic
    try:
        data = CreateNewsSchema(title=title, date=date, description=description)
    except ValidationError as e:
        # Convert Pydantic errors into FastAPI HTTPException
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=e.errors(),
        )

    # 2) Prevent duplicate title+date
    if (
        db.query(LatestNews)
        .filter(LatestNews.title == data.title, LatestNews.date == data.date)
        .first()
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "news_exists",
                "message": f"A news item titled '{data.title}' on {data.date} already exists.",
            },
        )

    # 3) Build filename
    slug = "".join(c for c in data.title.lower().replace(" ", "_") if c.isalnum() or c == "_")
    date_str = data.date.strftime("%Y%m%d")
    ext = os.path.splitext(photo.filename)[1] or ".jpg"
    filename = f"{slug}_{date_str}{ext}"
    filepath = os.path.join(UPLOAD_DIR, filename)

    # 4) Save & crop
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
            detail={"error": "invalid_image", "message": "Uploaded file is not a valid image."},
        )

    # 5) Persist record
    new_news = LatestNews(
        title=data.title,
        date=data.date,
        description=data.description,
        photo=f"/uploads/news/{filename}",
    )
    db.add(new_news)
    db.commit()
    db.refresh(new_news)

    # 6) Build full URL
    photo_url = str(request.base_url).rstrip("/") + new_news.photo

    # 7) Return
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
                "photo": photo_url,
                "created_at": new_news.created_at.isoformat(),
                "updated_at": new_news.updated_at.isoformat(),
            },
        },
    )