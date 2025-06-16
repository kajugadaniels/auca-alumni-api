from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import asc, desc, func
from sqlalchemy.orm import Session

from database import get_db
from models import Students
from schemas.student import StudentSchema, StudentListResponse

router = APIRouter()

@router.get(
    "",
    response_model=StudentListResponse,
    summary="Retrieve a paginated list of students with metadata",
)
def get_students(
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
    - total count of matching records
    - current page and page_size
    - next_page and prev_page indicators
    """
    base_q = db.query(Students)

    # Apply search filter
    if search:
        term = f"%{search.strip()}%"
        base_q = base_q.filter(
            Students.first_name.ilike(term) | Students.last_name.ilike(term)
        )

    # Total count on filtered set
    total = base_q.with_entities(func.count()).scalar()  # single-count query

    # Apply ordering
    direction = asc if order == "asc" else desc
    column = getattr(Students, sort_by)
    ordered_q = base_q.order_by(direction(column))

    # Pagination
    offset = (page - 1) * page_size
    students = ordered_q.offset(offset).limit(page_size).all()

    if not students and page != 1:
        raise HTTPException(status_code=404, detail="Page out of range")

    # Calculate prev/next page numbers
    prev_page = page - 1 if page > 1 else None
    next_page = page + 1 if offset + len(students) < total else None

    return StudentListResponse(
        total=total,
        page=page,
        page_size=page_size,
        next_page=next_page,
        prev_page=prev_page,
        items=students,
    )

# git commit -m "feat: enhance students router with total count and prev/next page"
