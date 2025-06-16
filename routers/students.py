from models import *
from database import *
from schemas.student import *
from sqlalchemy import asc, desc
from typing import List, Optional
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, HTTPException, Query

router = APIRouter()

@router.get(
    "",
    response_model=StudentListResponse,
    summary="Retrieve students with pagination, search, and sorting",
)
def get_students(
    request: Request,
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
    Retrieve a paginated list of students, with total count and navigation links.
    """
    # Base query
    base_q = db.query(Students)

    # Search filter
    if search:
        term = f"%{search.strip()}%"
        base_q = base_q.filter(
            Students.first_name.ilike(term) | Students.last_name.ilike(term)
        )

    # Total count
    total = base_q.with_entities(func.count()).scalar()  # COUNT(*) on filtered set

    # Sorting
    direction = asc if order == "asc" else desc
    column = getattr(Students, sort_by)
    base_q = base_q.order_by(direction(column))

    # Pagination calculations
    total_pages = ceil(total / page_size) if total else 1
    if page > total_pages and total > 0:
        raise HTTPException(status_code=404, detail="Page out of range")

    offset = (page - 1) * page_size
    items = base_q.offset(offset).limit(page_size).all()

    # Build next/prev page numbers
    next_page = page + 1 if page < total_pages else None
    prev_page = page - 1 if page > 1 else None

    return StudentListResponse(
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        next_page=next_page,
        prev_page=prev_page,
        items=items,
    )
