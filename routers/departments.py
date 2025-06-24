from typing import Optional
import os
import datetime

from fastapi import (
    APIRouter, Depends, HTTPException,
    Query, Request, status, Body
)
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import asc, desc, func

from database import get_db
from models import Departments, Faculties
from schemas.department import (
    CreateDepartmentSchema,
    DepartmentSchema,
    DepartmentListResponse,
    FacultyNestedSchema,
)
from routers.auth import get_current_user

router = APIRouter(
    prefix="/departments",
    tags=["departments"],
    dependencies=[Depends(get_current_user)],
)

@router.get(
    "/",
    response_model=DepartmentListResponse,
    summary="List departments with pagination, search, and sorting",
)
def list_departments(
    request: Request,
    *,
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Filter by department name"),
    sort_by: str = Query(
        "created_at",
        regex="^(id|name|created_at)$",
        description="Field to sort by"
    ),
    order: str = Query("asc", regex="^(asc|desc)$", description="Sort direction"),
) -> DepartmentListResponse:
    total = db.query(func.count(Departments.id)).scalar()
    q = db.query(Departments)
    if search:
        q = q.filter(Departments.name.ilike(f"%{search.strip()}%"))
    direction = asc if order == "asc" else desc
    q = q.order_by(direction(getattr(Departments, sort_by)))
    offset = (page - 1) * page_size
    raw = q.offset(offset).limit(page_size).all()
    if not raw and page != 1:
        raise HTTPException(status_code=404, detail="Page out of range")

    items = []
    for dept in raw:
        faculty = db.query(Faculties).get(dept.faculty_id)
        if not faculty:
            raise HTTPException(
                status_code=404,
                detail={"error": "faculty_not_found", "message": f"Faculty {dept.faculty_id} not found"},
            )
        items.append(
            DepartmentSchema(
                id=dept.id,
                faculty=FacultyNestedSchema.model_validate(faculty),
                name=dept.name,
                created_at=dept.created_at,
                updated_at=dept.updated_at,
            )
        )

    def make_url(p: int) -> str:
        return str(request.url.include_query_params(page=p, page_size=page_size))

    return DepartmentListResponse(
        total=total,
        page=page,
        page_size=page_size,
        next_page=make_url(page+1) if offset + len(items) < total else None,
        prev_page=make_url(page-1) if page > 1 else None,
        items=items,
    )

@router.post(
    "/add",
    response_model=DepartmentSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new department",
)
def add_department(
    data: CreateDepartmentSchema = Body(...),
    db: Session = Depends(get_db),
):
    # 1) Validate faculty exists
    faculty = db.query(Faculties).get(data.faculty_id)
    if not faculty:
        raise HTTPException(
            status_code=400,
            detail={"error": "faculty_not_found", "message": f"No faculty with ID {data.faculty_id}"}
        )

    # 2) Prevent duplicate name under same faculty
    if (
        db.query(Departments)
        .filter_by(faculty_id=data.faculty_id, name=data.name.strip())
        .first()
    ):
        raise HTTPException(
            status_code=400,
            detail={"error": "duplicate_department", "message": "Department already exists under this faculty"}
        )

    # 3) Persist
    dept = Departments(
        faculty_id=data.faculty_id,
        name=data.name.strip(),
    )
    db.add(dept)
    db.commit()
    db.refresh(dept)

    return DepartmentSchema(
        id=dept.id,
        faculty=FacultyNestedSchema.model_validate(faculty),
        name=dept.name,
        created_at=dept.created_at,
        updated_at=dept.updated_at,
    )

@router.get(
    "/{dept_id}",
    response_model=DepartmentSchema,
    summary="Get a single department by ID",
)
def get_department(
    dept_id: int,
    db: Session = Depends(get_db),
):
    dept = db.query(Departments).get(dept_id)
    if not dept:
        raise HTTPException(status_code=404, detail="Department not found")
    faculty = db.query(Faculties).get(dept.faculty_id)
    if not faculty:
        raise HTTPException(status_code=404, detail="Faculty not found")

    return DepartmentSchema(
        id=dept.id,
        faculty=FacultyNestedSchema.model_validate(faculty),
        name=dept.name,
        created_at=dept.created_at,
        updated_at=dept.updated_at,
    )

