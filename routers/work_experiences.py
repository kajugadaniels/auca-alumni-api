import datetime
from typing import Optional

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
    Query,
    Request,
)
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import asc, desc, func

from database import get_db
from models import WorkExperiences, Users
from schemas.work_experiences import (
    CreateWorkExperienceSchema,
    WorkExperienceSchema,
    WorkExperienceListResponse,
)
from routers.auth import get_current_user

router = APIRouter(
    prefix="/work-experiences",
    tags=["work-experiences"],
    dependencies=[Depends(get_current_user)],
)

# ------------------------------------------------------------------------
# GET /work-experiences: list with pagination and embedded user
# ------------------------------------------------------------------------
@router.get(
    "/",
    response_model=WorkExperienceListResponse,
    summary="Retrieve a paginated list of work experiences with user info",
)
def list_work_experiences(
    request: Request,
    *,
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Filter by company or job title"),
    sort_by: str = Query(
        "created_at",
        regex="^(id|start_date|created_at)$",
        description="Field to sort by",
    ),
    order: str = Query(
        "desc",
        regex="^(asc|desc)$",
        description="Sort direction",
    ),
) -> WorkExperienceListResponse:
    # 1) Total count
    total = db.query(func.count(WorkExperiences.id)).scalar()

    # 2) Base query + optional search
    query = db.query(WorkExperiences)
    if search:
        term = f"%{search.strip()}%"
        query = query.filter(
            WorkExperiences.company.ilike(term) |
            WorkExperiences.job_title.ilike(term)
        )

    # 3) Ordering
    direction = asc if order == "asc" else desc
    column = getattr(WorkExperiences, sort_by)
    query = query.order_by(direction(column))

    # 4) Pagination
    offset = (page - 1) * page_size
    raw_items = query.offset(offset).limit(page_size).all()
    if not raw_items and page != 1:
        raise HTTPException(status_code=404, detail="Page out of range")

    # 5) Build items including nested user
    items = []
    for exp in raw_items:
        user = db.query(Users).get(exp.user_id) if exp.user_id else None
        if not user:
            continue  # or raise if required
        items.append(
            WorkExperienceSchema(
                id=exp.id,
                company=exp.company,
                employer=exp.employer,
                job_title=exp.job_title,
                job_description=exp.job_description,
                start_date=exp.start_date,
                end_date=exp.end_date,
                created_at=exp.created_at,
                updated_at=exp.updated_at,
                user=user,
            )
        )

    # 6) Navigation URLs
    def make_url(p: int) -> str:
        return str(request.url.include_query_params(page=p, page_size=page_size))

    prev_page = make_url(page - 1) if page > 1 else None
    next_page = make_url(page + 1) if offset + len(items) < total else None

    return WorkExperienceListResponse(
        total=total,
        page=page,
        page_size=page_size,
        next_page=next_page,
        prev_page=prev_page,
        items=items,
    )

# ------------------------------------------------------------------------
# POST /work-experiences/add: create new work experience
# ------------------------------------------------------------------------
@router.post(
    "/add",
    status_code=status.HTTP_201_CREATED,
    summary="Create a new work experience entry",
)
def add_work_experience(
    data: CreateWorkExperienceSchema,
    db: Session = Depends(get_db),
):
    # 1) Verify user exists
    user = db.query(Users).get(data.user_id)
    if not user:
        raise HTTPException(
            status_code=400,
            detail={"error": "invalid_user", "message": f"No user found with ID {data.user_id}."}
        )

    # 2) Prevent exact duplicate (company + user + start_date)
    existing = (
        db.query(WorkExperiences)
        .filter_by(
            company=data.company.strip(),
            user_id=data.user_id,
            start_date=data.start_date
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=400,
            detail={"error": "experience_exists", "message": "This work experience already exists."}
        )

    # 3) Create and persist
    new_exp = WorkExperiences(
        company=data.company.strip(),
        employer=data.employer.strip(),
        job_title=data.job_title.strip(),
        job_description=data.job_description.strip(),
        start_date=data.start_date,
        end_date=data.end_date,
        user_id=data.user_id,
    )
    db.add(new_exp)
    db.commit()
    db.refresh(new_exp)

    # 4) Return with nested user
    return WorkExperienceSchema(
        id=new_exp.id,
        company=new_exp.company,
        employer=new_exp.employer,
        job_title=new_exp.job_title,
        job_description=new_exp.job_description,
        start_date=new_exp.start_date,
        end_date=new_exp.end_date,
        created_at=new_exp.created_at,
        updated_at=new_exp.updated_at,
        user=user,
    )

# ------------------------------------------------------------------------
# GET /work-experiences/{exp_id}: retrieve one experience
# ------------------------------------------------------------------------
@router.get(
    "/{exp_id}",
    response_model=WorkExperienceSchema,
    summary="Retrieve detailed information for a single work experience",
)
def get_work_experience(
    exp_id: int,
    db: Session = Depends(get_db),
):
    exp = db.query(WorkExperiences).get(exp_id)
    if not exp:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "message": f"No experience found with ID {exp_id}."}
        )
    user = db.query(Users).get(exp.user_id) if exp.user_id else None
    return WorkExperienceSchema(
        id=exp.id,
        company=exp.company,
        employer=exp.employer,
        job_title=exp.job_title,
        job_description=exp.job_description,
        start_date=exp.start_date,
        end_date=exp.end_date,
        created_at=exp.created_at,
        updated_at=exp.updated_at,
        user=user,
    )

# ------------------------------------------------------------------------
# PUT /work-experiences/{exp_id}/update: update an existing experience
# ------------------------------------------------------------------------
@router.put(
    "/{exp_id}/update",
    response_model=WorkExperienceSchema,
    summary="Update a work experience by ID",
)
def update_work_experience(
    exp_id: int,
    data: CreateWorkExperienceSchema,
    db: Session = Depends(get_db),
):
    exp = db.query(WorkExperiences).get(exp_id)
    if not exp:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "message": f"No experience found with ID {exp_id}."}
        )
    user = db.query(Users).get(data.user_id)
    if not user:
        raise HTTPException(
            status_code=400,
            detail={"error": "invalid_user", "message": f"No user found with ID {data.user_id}."}
        )

    # Prevent duplicate on another record
    dup = (
        db.query(WorkExperiences)
        .filter(
            WorkExperiences.id != exp_id,
            WorkExperiences.company == data.company.strip(),
            WorkExperiences.user_id == data.user_id,
            WorkExperiences.start_date == data.start_date,
        )
        .first()
    )
    if dup:
        raise HTTPException(
            status_code=400,
            detail={"error": "duplicate", "message": "Another identical experience exists."}
        )

    # Apply updates
    exp.company = data.company.strip()
    exp.employer = data.employer.strip()
    exp.job_title = data.job_title.strip()
    exp.job_description = data.job_description.strip()
    exp.start_date = data.start_date
    exp.end_date = data.end_date
    exp.user_id = data.user_id

    db.add(exp)
    db.commit()
    db.refresh(exp)

    return WorkExperienceSchema(
        id=exp.id,
        company=exp.company,
        employer=exp.employer,
        job_title=exp.job_title,
        job_description=exp.job_description,
        start_date=exp.start_date,
        end_date=exp.end_date,
        created_at=exp.created_at,
        updated_at=exp.updated_at,
        user=user,
    )
