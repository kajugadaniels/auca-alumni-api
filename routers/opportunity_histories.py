from fastapi import (
    APIRouter, Depends, HTTPException, Query, Request, status, Body,
)
from typing import Optional
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, asc, desc

from database import get_db
from models import OpportunityHistories, Users, Opportunities
from schemas.opportunity_histories import (
    CreateHistorySchema,
    OpportunityHistorySchema,
    OpportunityHistoryListResponse,
    UserInfoSchema,
)
from routers.auth import get_current_user

router = APIRouter(
    prefix="/opportunity-histories",
    tags=["opportunity-histories"],
    dependencies=[Depends(get_current_user)],
)

@router.get(
    "/",
    response_model=OpportunityHistoryListResponse,
    summary="List paginated opportunity histories, including nested user info",
)
def list_histories(
    request: Request,
    *,
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    opportunity_id: int | None = Query(None, description="Filter by opportunity_id"),
    user_id: int | None = Query(None, description="Filter by user_id"),
    sort_by: str = Query(
        "created_at",
        regex="^(id|created_at|updated_at)$",
        description="Field to sort by",
    ),
    order: str = Query("desc", regex="^(asc|desc)$", description="Sort direction"),
) -> OpportunityHistoryListResponse:
    # 1) Build base query and count
    query = db.query(OpportunityHistories)
    if opportunity_id:
        query = query.filter(OpportunityHistories.opportunity_id == opportunity_id)
    if user_id:
        query = query.filter(OpportunityHistories.user_id == user_id)

    total = query.with_entities(func.count()).scalar()

    # 2) Sort & paginate
    direction = asc if order == "asc" else desc
    column = getattr(OpportunityHistories, sort_by)
    raw = (
        query
        .order_by(direction(column))
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    if not raw and page != 1:
        raise HTTPException(status_code=404, detail="Page out of range")

    # 3) Build response items
    items = []
    for hist in raw:
        usr = db.query(Users).get(hist.user_id)
        opp = db.query(Opportunities).get(hist.opportunity_id)
        if not usr or not opp:
            raise HTTPException(status_code=500, detail="Referenced user or opportunity not found")

        user_info = UserInfoSchema.model_validate(usr)
        opp_info  = OpportunityInfoSchema.model_validate(opp)

        items.append(
            OpportunityHistorySchema(
                id=hist.id,
                opportunity=opp_info,
                user=user_info,
                comment=hist.comment,
                status=hist.status,
                created_at=hist.created_at,
                updated_at=hist.updated_at,
            )
        )

    # 4) Navigation URLs
    def make_url(p: int) -> str:
        return str(request.url.include_query_params(page=p, page_size=page_size))

    prev_page = make_url(page - 1) if page > 1 else None
    next_page = make_url(page + 1) if (page * page_size) < total else None

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
    status_code=status.HTTP_201_CREATED,
    summary="Create a new opportunity history entry",
)
def add_history(
    data: CreateHistorySchema = Body(...),
    db: Session = Depends(get_db),
):
    """
    1) Ensure both user_id and opportunity_id exist.
    2) Persist the history entry.
    3) Return nested user and opportunity details.
    """
    # Validate user
    if not db.query(Users).get(data.user_id):
        raise HTTPException(status_code=400, detail="Invalid user_id")

    # Validate opportunity
    opp = db.query(Opportunities).get(data.opportunity_id)
    if not opp:
        raise HTTPException(status_code=400, detail="Invalid opportunity_id")

    # Persist
    new_hist = OpportunityHistories(
        opportunity_id=data.opportunity_id,
        user_id=data.user_id,
        comment=data.comment,
        status=data.status,
    )
    db.add(new_hist)
    db.commit()
    db.refresh(new_hist)

    # Build nested objects
    user_info = UserInfoSchema.model_validate(db.query(Users).get(new_hist.user_id))
    opp_info  = OpportunityInfoSchema.model_validate(opp)

    history_data = OpportunityHistorySchema(
        id=new_hist.id,
        opportunity=opp_info,
        user=user_info,
        comment=new_hist.comment,
        status=new_hist.status,
        created_at=new_hist.created_at,
        updated_at=new_hist.updated_at,
    ).model_dump(mode="json")

    return JSONResponse(
        status_code=201,
        content={
            "status": "success",
            "message": "History entry created.",
            "history": history_data,
        },
    )

@router.get(
    "/{history_id}",
    response_model=OpportunityHistorySchema,
    summary="Retrieve detailed opportunity history by ID with nested info",
)
def get_history(
    history_id: int,
    db: Session = Depends(get_db),
):
    """
    1) Fetch history, then its user and opportunity.
    2) Return all with nested objects.
    """
    hist = db.query(OpportunityHistories).get(history_id)
    if not hist:
        raise HTTPException(status_code=404, detail="History not found")

    usr = db.query(Users).get(hist.user_id)
    opp = db.query(Opportunities).get(hist.opportunity_id)
    if not usr:
        raise HTTPException(status_code=500, detail="User referenced not found")
    if not opp:
        raise HTTPException(status_code=500, detail="Opportunity referenced not found")

    user_info = UserInfoSchema.model_validate(usr)
    opp_info  = OpportunityInfoSchema.model_validate(opp)

    return OpportunityHistorySchema(
        id=hist.id,
        opportunity=opp_info,
        user=user_info,
        comment=hist.comment,
        status=hist.status,
        created_at=hist.created_at,
        updated_at=hist.updated_at,
    )

@router.put(
    "/{history_id}/update",
    response_model=OpportunityHistorySchema,
    summary="Update an existing opportunity history by ID",
)
def update_history(
    history_id: int,
    data: CreateHistorySchema = Body(...),
    db: Session = Depends(get_db),
):
    hist = db.query(OpportunityHistories).get(history_id)
    if not hist:
        raise HTTPException(status_code=404, detail="History not found")

    # FK checks
    if not db.query(Users).get(data.user_id):
        raise HTTPException(status_code=400, detail="Invalid user_id")
    if not db.query(Opportunities).get(data.opportunity_id):
        raise HTTPException(status_code=400, detail="Invalid opportunity_id")

    # Apply updates
    hist.opportunity_id = data.opportunity_id
    hist.user_id = data.user_id
    hist.comment = data.comment
    hist.status = data.status
    db.commit()
    db.refresh(hist)

    # Build nested user info
    usr = db.query(Users).get(hist.user_id)
    user_info = UserInfoSchema.model_validate(usr)

    return OpportunityHistorySchema(
        id=hist.id,
        opportunity_id=hist.opportunity_id,
        user=user_info,
        comment=hist.comment,
        status=hist.status,
        created_at=hist.created_at,
        updated_at=hist.updated_at,
    )

@router.delete(
    "/{history_id}/delete",
    status_code=status.HTTP_200_OK,
    summary="Delete a specific opportunity history entry",
)
def delete_history(
    history_id: int,
    db: Session = Depends(get_db),
):
    hist = db.query(OpportunityHistories).get(history_id)
    if not hist:
        raise HTTPException(status_code=404, detail="History not found")

    db.delete(hist)
    db.commit()
    return JSONResponse(
        status_code=200,
        content={"status": "success", "message": f"History ID {history_id} deleted."},
    )
