import datetime
from typing import Optional

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Request,
    status,
    Form,
)
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import asc, desc, func

from database import get_db
from models import OpportunityHistories, Users, Opportunities
from schemas.opportunity_history import (
    CreateOpportunityHistorySchema,
    OpportunityHistorySchema,
    OpportunityHistoryListResponse,
    OpportunityUserSchema,
    OpportunitySummarySchema,
)
from routers.auth import get_current_user

router = APIRouter(
    prefix="/opportunity-histories",
    tags=["opportunity_histories"],
    dependencies=[Depends(get_current_user)],
)

@router.get(
    "/",
    response_model=OpportunityHistoryListResponse,
    summary="List paginated history entries with nested user & opportunity",
)
def list_history(
    request: Request,
    *,
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Filter by comment text"),
    sort_by: str = Query(
        "created_at",
        regex="^(id|created_at)$",
        description="Field to sort by",
    ),
    order: str = Query(
        "desc", regex="^(asc|desc)$", description="Sort direction"
    ),
) -> OpportunityHistoryListResponse:
    # 1) Total count
    total = db.query(func.count(OpportunityHistories.id)).scalar()

    # 2) Base query + optional search
    q = db.query(OpportunityHistories)
    if search:
        term = f"%{search.strip()}%"
        q = q.filter(OpportunityHistories.comment.ilike(term))

    # 3) Ordering
    direction = asc if order == "asc" else desc
    q = q.order_by(direction(getattr(OpportunityHistories, sort_by)))

    # 4) Pagination
    offset = (page - 1) * page_size
    raw = q.offset(offset).limit(page_size).all()
    if not raw and page != 1:
        raise HTTPException(status_code=404, detail="Page out of range")

    # 5) Build items
    base = str(request.base_url).rstrip("/")
    items = []
    for h in raw:
        user = db.query(Users).get(h.user_id)
        opp = db.query(Opportunities).get(h.opportunity_id)
        if not user or not opp:
            raise HTTPException(
                status_code=404,
                detail="Related user or opportunity not found"
            )
        items.append(
            OpportunityHistorySchema(
                **{
                    **h.__dict__,
                    "user": OpportunityUserSchema.model_validate(user),
                    "opportunity": OpportunitySummarySchema.model_validate(opp),
                }
            )
        )

    # 6) Navigation URLs
    def make_url(p: int) -> str:
        return str(request.url.include_query_params(page=p, page_size=page_size))

    prev_page = make_url(page - 1) if page > 1 else None
    next_page = make_url(page + 1) if offset + len(items) < total else None

    return OpportunityHistoryListResponse(
        total=total,
        page=page,
        page_size=page_size,
        next_page=next_page,
        prev_page=prev_page,
        items=items,
    )

@router.post(
    "/add",
    response_model=OpportunityHistorySchema,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new opportunity history entry",
)
def add_history(
    request: Request,
    opportunity_id: int = Form(..., description="ID of related opportunity"),
    user_id: int = Form(..., description="ID of user making the comment"),
    comment: str = Form(..., min_length=5, description="Comment text"),
    status: str = Form(..., description="Status update"),
    db: Session = Depends(get_db),
):
    # 1) Validate payload
    data = CreateOpportunityHistorySchema(
        opportunity_id=opportunity_id,
        user_id=user_id,
        comment=comment,
        status=status,
    )

    # 2) Existence checks
    if not db.query(Opportunities).get(data.opportunity_id):
        raise HTTPException(status_code=404, detail="Opportunity not found")
    if not db.query(Users).get(data.user_id):
        raise HTTPException(status_code=404, detail="User not found")

    # 3) Persist
    new_h = OpportunityHistories(
        opportunity_id=data.opportunity_id,
        user_id=data.user_id,
        comment=data.comment,
        status=data.status,
    )
    db.add(new_h)
    db.commit()
    db.refresh(new_h)

    # 4) Nested objects
    user = db.query(Users).get(new_h.user_id)
    opp = db.query(Opportunities).get(new_h.opportunity_id)

    return OpportunityHistorySchema(
        **{
            **new_h.__dict__,
            "user": OpportunityUserSchema.model_validate(user),
            "opportunity": OpportunitySummarySchema.model_validate(opp),
        }
    )

@router.get(
    "/{hist_id}",
    response_model=OpportunityHistorySchema,
    summary="Retrieve a single history entry by ID",
)
def get_history(
    hist_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    h = db.query(OpportunityHistories).get(hist_id)
    if not h:
        raise HTTPException(status_code=404, detail="History entry not found")

    user = db.query(Users).get(h.user_id)
    opp = db.query(Opportunities).get(h.opportunity_id)
    return OpportunityHistorySchema(
        **{
            **h.__dict__,
            "user": OpportunityUserSchema.model_validate(user),
            "opportunity": OpportunitySummarySchema.model_validate(opp),
        }
    )

@router.put(
    "/{hist_id}/update",
    response_model=OpportunityHistorySchema,
    summary="Update an existing history entry by ID",
)
def update_history(
    hist_id: int,
    comment: str = Form(..., min_length=5, description="Updated comment"),
    status: str = Form(..., description="Updated status"),
    db: Session = Depends(get_db),
):
    h = db.query(OpportunityHistories).get(hist_id)
    if not h:
        raise HTTPException(status_code=404, detail="History entry not found")

    h.comment = comment
    h.status = status
    db.commit()
    db.refresh(h)

    user = db.query(Users).get(h.user_id)
    opp = db.query(Opportunities).get(h.opportunity_id)
    return OpportunityHistorySchema(
        **{
            **h.__dict__,
            "user": OpportunityUserSchema.model_validate(user),
            "opportunity": OpportunitySummarySchema.model_validate(opp),
        }
    )
