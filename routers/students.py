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
    response_model=List[StudentSchema],
    summary="Retrieve a paginated list of students",
)
def get_students(
    *,
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(10, ge=1, le=100, description="Number of items per page"),
    search: Optional[str] = Query(None, description="Filter by first or last name"),
    sort_by: str = Query(
        "created_at",
        regex="^(id|id_number|first_name|last_name|created_at)$",
        description="Field to sort by",
    ),
    order: str = Query(
        "desc", regex="^(asc|desc)$", description="Sort direction"
    ),
) -> List[StudentSchema]:
    """
    Retrieve a paginated list of students, optionally filtered and ordered.
    """
    query = db.query(Students)

    # 1) Search filter
    if search:
        term = f"%{search.strip()}%"
        query = query.filter(
            Students.first_name.ilike(term) | Students.last_name.ilike(term)
        )

    # 2) Ordering
    direction = asc if order == "asc" else desc
    column = getattr(Students, sort_by)
    query = query.order_by(direction(column))

    # 3) Pagination
    offset = (page - 1) * page_size
    students = query.offset(offset).limit(page_size).all()

    if not students and page != 1:
        raise HTTPException(status_code=404, detail="Page out of range")

    return students

# git commit -m "Add students router with pagination, search, and sorting"
