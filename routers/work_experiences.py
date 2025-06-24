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
