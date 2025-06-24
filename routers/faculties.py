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

# ------------------------------------------------------------------------
# GET /faculties/{faculty_id}: retrieve detailed faculty by ID
# ------------------------------------------------------------------------
@router.get(
    "/{faculty_id}",
    response_model=FacultySchema,
    summary="Retrieve detailed information for a single faculty by ID",
)
def get_faculty(
    faculty_id: int,
    db: Session = Depends(get_db),
):
    """
    Fetch a single faculty by ID.
    Returns 404 if not found.
    """
    fac = db.query(Faculties).get(faculty_id)
    if not fac:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "faculty_not_found", "message": f"No faculty found with ID {faculty_id}."},
        )
    return FacultySchema.from_orm(fac)

# ------------------------------------------------------------------------
# PUT /faculties/{faculty_id}/update: update an existing faculty by ID
# ------------------------------------------------------------------------
@router.put(
    "/{faculty_id}/update",
    response_model=FacultySchema,
    summary="Update an existing faculty by ID",
)
def update_faculty(
    faculty_id: int,
    data: CreateFacultySchema = Body(...),
    db: Session = Depends(get_db),
):
    """
    Updates a faculty:
    - Validates via CreateFacultySchema
    - Prevents duplicate name on other records
    """
    fac = db.query(Faculties).get(faculty_id)
    if not fac:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "faculty_not_found", "message": f"No faculty found with ID {faculty_id}."},
        )

    # Duplicate name check
    if (
        db.query(Faculties)
        .filter(Faculties.id != faculty_id, Faculties.name == data.name)
        .first()
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "faculty_exists", "message": f"Another faculty named '{data.name}' already exists."},
        )

    # Apply updates
    fac.name = data.name
    fac.description = data.description
    db.add(fac)
    db.commit()
    db.refresh(fac)

    return FacultySchema.from_orm(fac)

# ------------------------------------------------------------------------
# DELETE /faculties/{faculty_id}/delete: delete a faculty
# ------------------------------------------------------------------------
@router.delete(
    "/{faculty_id}/delete",
    status_code=status.HTTP_200_OK,
    summary="Delete a specific faculty",
)
def delete_faculty(
    faculty_id: int,
    db: Session = Depends(get_db),
):
    """
    Deletes the faculty identified by `faculty_id`.
    """
    fac = db.query(Faculties).get(faculty_id)
    if not fac:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "faculty_not_found", "message": f"No faculty found with ID {faculty_id}."},
        )

    db.delete(fac)
    db.commit()
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"status": "success", "message": f"Faculty with ID {faculty_id} deleted successfully."},
    )
