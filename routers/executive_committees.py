import os
from io import BytesIO
import datetime
from typing import Optional

from fastapi import (
    APIRouter, Depends, HTTPException,
    File, UploadFile, Form, Request,
    Query, status
)
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import asc, desc, func
from PIL import Image, UnidentifiedImageError

from database import get_db
from models import ExecutiveComittes
from schemas.executive_committees import (
    CreateExecutiveCommitteeSchema,
    ExecutiveCommitteeSchema,
    ExecutiveCommitteeListResponse,
)
from routers.auth import get_current_user

router = APIRouter(
    prefix="/executive-committees",
    tags=["executive-committees"],
    dependencies=[Depends(get_current_user)],
)

# Upload directory
UPLOAD_DIR = os.path.join(os.getcwd(), "uploads", "executive_committees")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ------------------------------------------------------------------------
# GET /executive-committees/
# ------------------------------------------------------------------------
@router.get(
    "/",
    response_model=ExecutiveCommitteeListResponse,
    summary="Get paginated list of executive committee members",
)
def list_committees(
    request: Request,
    *,
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Filter by name or position"),
    sort_by: str = Query(
        "created_at",
        regex="^(id|name|position|created_at)$",
        description="Field to sort by"
    ),
    order: str = Query("desc", regex="^(asc|desc)$", description="Sort direction"),
) -> ExecutiveCommitteeListResponse:
    total = db.query(func.count(ExecutiveComittes.id)).scalar()
    q = db.query(ExecutiveComittes)
    if search:
        term = f"%{search.strip()}%"
        q = q.filter(
            ExecutiveComittes.name.ilike(term)
            | ExecutiveComittes.position.ilike(term)
        )
    direction = asc if order == "asc" else desc
    q = q.order_by(direction(getattr(ExecutiveComittes, sort_by)))
    offset = (page - 1) * page_size
    raw = q.offset(offset).limit(page_size).all()
    if not raw and page != 1:
        raise HTTPException(status_code=404, detail="Page out of range")

    base = str(request.base_url).rstrip("/")
    items = [
        ExecutiveCommitteeSchema(
            **{
                **member.__dict__,
                "photo": f"{base}{member.photo}"
            }
        )
        for member in raw
    ]

    def make_url(p: int) -> str:
        return str(request.url.include_query_params(page=p, page_size=page_size))

    return ExecutiveCommitteeListResponse(
        total=total,
        page=page,
        page_size=page_size,
        next_page=make_url(page+1) if offset + len(items) < total else None,
        prev_page=make_url(page-1) if page > 1 else None,
        items=items,
    )
