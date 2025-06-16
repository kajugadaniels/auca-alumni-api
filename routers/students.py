from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import asc, desc, func
from sqlalchemy.orm import Session

from database import get_db
from models import Students
from schemas.student import StudentSchema, StudentListResponse

router = APIRouter()

@router.get(
    "",
    response_model=StudentListResponse,
    summary="Retrieve a paginated list of students with metadata and navigation URLs",
)
def get_students(
    request: Request,
    *,
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Filter by first or last name"),
    sort_by: str = Query(
        "created_at",
        regex="^(id|id_number|first_name|last_name|created_at)$",
        description="Field to sort by",
    ),
    order: str = Query(
        "desc", regex="^(asc|desc)$", description="Sort direction"
    ),
) -> StudentListResponse:
    """
    Retrieve students with:
    - total count of all records
    - current page and page_size
    - next_page and prev_page as full URLs
    """
    # 1) Total records (no filter)
    total = db.query(func.count(Students.id)).scalar()

    # 2) Build filtered + ordered query for items
    query = db.query(Students)
    if search:
        term = f"%{search.strip()}%"
        query = query.filter(
            Students.first_name.ilike(term) | Students.last_name.ilike(term)
        )

    direction = asc if order == "asc" else desc
    column = getattr(Students, sort_by)
    query = query.order_by(direction(column))

    # 3) Pagination
    offset = (page - 1) * page_size
    items = query.offset(offset).limit(page_size).all()

    # if out of range
    if not items and page != 1:
        raise HTTPException(status_code=404, detail="Page out of range")

    # 4) Build navigation URLs
    def make_url(p: int) -> str:
        return str(request.url.include_query_params(page=p, page_size=page_size))

    prev_page = make_url(page - 1) if page > 1 else None
    next_page = make_url(page + 1) if offset + len(items) < total else None

    return StudentListResponse(
        total=total,
        page=page,
        page_size=page_size,
        next_page=next_page,
        prev_page=prev_page,
        items=items,
    )