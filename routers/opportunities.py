import os
import datetime
from io import BytesIO
from typing import Optional

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    File,
    UploadFile,
    Form,
    Request,
    Query,
    status,
)
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import asc, desc, func
from PIL import Image, UnidentifiedImageError

from database import get_db
from models import Opportunities, Users
from schemas.opportunity import (
    CreateOpportunitySchema,
    OpportunitySchema,
    OpportunityListResponse,
    OpportunityUserSchema,
)
from routers.auth import get_current_user

router = APIRouter(
    prefix="/opportunities",
    tags=["opportunities"],
    dependencies=[Depends(get_current_user)],
)

# ensure upload folder
UPLOAD_DIR = os.path.join(os.getcwd(), "uploads", "opportunities")
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.get(
    "/",
    response_model=OpportunityListResponse,
    summary="Retrieve paginated list of opportunities with nested user data",
)
def list_opportunities(
    request: Request,
    *,
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Filter by title or description"),
    sort_by: str = Query(
        "created_at",
        regex="^(id|date|created_at)$",
        description="Field to sort by",
    ),
    order: str = Query(
        "desc", regex="^(asc|desc)$", description="Sort direction"
    ),
) -> OpportunityListResponse:
    # 1) Total count
    total = db.query(func.count(Opportunities.id)).scalar()

    # 2) Query with optional search
    q = db.query(Opportunities)
    if search:
        term = f"%{search.strip()}%"
        q = q.filter(
            Opportunities.title.ilike(term)
            | Opportunities.description.ilike(term)
        )

    # 3) Ordering
    direction = asc if order == "asc" else desc
    q = q.order_by(direction(getattr(Opportunities, sort_by)))

    # 4) Pagination
    offset = (page - 1) * page_size
    raw = q.offset(offset).limit(page_size).all()
    if not raw and page != 1:
        raise HTTPException(status_code=404, detail="Page out of range")

    # 5) Build items
    base = str(request.base_url).rstrip("/")
    items = []
    for op in raw:
        # nested user lookup
        user = db.query(Users).get(op.user_id)
        if not user:
            raise HTTPException(
                status_code=404,
                detail={"error": "user_not_found", "message": f"User {op.user_id} not found"},
            )
        photo_url = f"{base}{op.photo}"
        items.append(
            OpportunitySchema(
                id=op.id,
                photo=photo_url,
                title=op.title,
                description=op.description,
                date=op.date,
                status=op.status,
                link=op.link,
                created_at=op.created_at,
                updated_at=op.updated_at,
                user=OpportunityUserSchema.from_attributes(user),
            )
        )

    # 6) Navigation URLs
    def make_url(p: int) -> str:
        return str(request.url.include_query_params(page=p, page_size=page_size))

    prev_page = make_url(page - 1) if page > 1 else None
    next_page = make_url(page + 1) if offset + len(items) < total else None

    return OpportunityListResponse(
        total=total,
        page=page,
        page_size=page_size,
        next_page=next_page,
        prev_page=prev_page,
        items=items,
    )

