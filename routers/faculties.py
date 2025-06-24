from typing import Optional
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
    Query,
    Request,
    Body,
)
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, asc, desc

from database import get_db
from models import Faculties
from schemas.faculty import (
    CreateFacultySchema,
    FacultySchema,
    FacultyListResponse,
)
from routers.auth import get_current_user

router = APIRouter(
    prefix="/faculties",
    tags=["faculties"],
    dependencies=[Depends(get_current_user)],
)

# ------------------------------------------------------------------------
# GET /faculties: list all faculties with pagination
# ------------------------------------------------------------------------
@router.get(
    "/",
    response_model=FacultyListResponse,
    summary="Retrieve a paginated list of faculties with full metadata",
)
def list_faculties(
    request: Request,
    *,
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Filter by name or description"),
    sort_by: str = Query(
        "created_at",
        regex="^(id|name|created_at)$",
        description="Field to sort by; defaults to `created_at`",
    ),
    order: str = Query(
        "desc",
        regex="^(asc|desc)$",
        description="Sort direction; defaults to descending (latest first)",
    ),
) -> FacultyListResponse:
    """
    Retrieve faculties with:
    - total count
    - pagination metadata
    """
    # 1) Total count
    total = db.query(func.count(Faculties.id)).scalar()

    # 2) Base query
    query = db.query(Faculties)
    if search:
        term = f"%{search.strip()}%"
        query = query.filter(
            Faculties.name.ilike(term) | Faculties.description.ilike(term)
        )

    # 3) Ordering
    direction = asc if order == "asc" else desc
    column = getattr(Faculties, sort_by)
    query = query.order_by(direction(column))

    # 4) Pagination
    offset = (page - 1) * page_size
    raw_items = query.offset(offset).limit(page_size).all()
    if not raw_items and page != 1:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Page out of range")

    # 5) Build items
    items = [
        FacultySchema(
            id=fac.id,
            name=fac.name,
            description=fac.description,
            created_at=fac.created_at,
            updated_at=fac.updated_at,
        )
        for fac in raw_items
    ]

    # 6) Navigation URLs
    def make_url(p: int) -> str:
        return str(request.url.include_query_params(page=p, page_size=page_size))

    prev_page = make_url(page - 1) if page > 1 else None
    next_page = make_url(page + 1) if offset + len(items) < total else None

    return FacultyListResponse(
        total=total,
        page=page,
        page_size=page_size,
        prev_page=prev_page,
        next_page=next_page,
        items=items,
    )

# ------------------------------------------------------------------------
# POST /faculties/add: create a new faculty
# ------------------------------------------------------------------------
@router.post(
    "/add",
    status_code=status.HTTP_201_CREATED,
    summary="Create a new faculty",
)
def add_faculty(
    data: CreateFacultySchema = Body(...),
    db: Session = Depends(get_db),
):
    """
    Creates a new faculty:
    - Validates via CreateFacultySchema
    - Prevents duplicate name
    """
    # 1) Duplicate check
    if db.query(Faculties).filter_by(name=data.name).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "faculty_exists",
                "message": f"A faculty named '{data.name}' already exists."
            },
        )

    # 2) Persist record
    new_fac = Faculties(name=data.name, description=data.description)
    db.add(new_fac)
    db.commit()
    db.refresh(new_fac)

    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={
            "status": "success",
            "message": "Faculty created successfully.",
            "faculty": {
                "id": new_fac.id,
                "name": new_fac.name,
                "description": new_fac.description,
                "created_at": new_fac.created_at.isoformat(),
                "updated_at": new_fac.updated_at.isoformat(),
            },
        },
    )
