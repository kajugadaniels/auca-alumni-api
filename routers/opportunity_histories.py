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
    opportunity_id: Optional[int] = Query(None, description="Filter by opportunity_id"),
    user_id: Optional[int] = Query(None, description="Filter by user_id"),
    sort_by: str = Query(
        "created_at",
        regex="^(id|created_at|updated_at)$",
        description="Field to sort by",
    ),
    order: str = Query("desc", regex="^(asc|desc)$", description="Sort direction"),
) -> OpportunityHistoryListResponse:
    # 1) Count
    query = db.query(OpportunityHistories)
    if opportunity_id:
        query = query.filter(OpportunityHistories.opportunity_id == opportunity_id)
    if user_id:
        query = query.filter(OpportunityHistories.user_id == user_id)

    total = query.with_entities(func.count()).scalar()

    # 2) Sort & paginate
    direction = asc if order == "asc" else desc
    column = getattr(OpportunityHistories, sort_by)
    items_q = query.order_by(direction(column)).offset((page - 1) * page_size).limit(page_size).all()
    if not items_q and page != 1:
        raise HTTPException(status_code=404, detail="Page out of range")

    # 3) Build response items
    results = []
    for hist in items_q:
        user = db.query(Users).get(hist.user_id)
        if not user:
            raise HTTPException(status_code=500, detail="User data missing")
        results.append(
            OpportunityHistorySchema(
                id=hist.id,
                opportunity_id=hist.opportunity_id,
                user=UserInfoSchema.from_attributes(user),
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
        items=results,
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
    # 1) Validate FK existence
    if not db.query(Users).get(data.user_id):
        raise HTTPException(status_code=400, detail="Invalid user_id")
    if not db.query(Opportunities).get(data.opportunity_id):
        raise HTTPException(status_code=400, detail="Invalid opportunity_id")

    # 2) Persist
    new_hist = OpportunityHistories(
        opportunity_id=data.opportunity_id,
        user_id=data.user_id,
        comment=data.comment,
        status=data.status,
    )
    db.add(new_hist)
    db.commit()
    db.refresh(new_hist)

    # 3) Return nested schema
    user = db.query(Users).get(data.user_id)
    return JSONResponse(
        status_code=201,
        content={
            "status": "success",
            "message": "History entry created.",
            "history": OpportunityHistorySchema(
                id=new_hist.id,
                opportunity_id=new_hist.opportunity_id,
                user=UserInfoSchema.from_attributes(user),
                comment=new_hist.comment,
                status=new_hist.status,
                created_at=new_hist.created_at,
                updated_at=new_hist.updated_at,
            ).model_dump(),
        },
    )

@router.get(
    "/{history_id}",
    response_model=OpportunityHistorySchema,
    summary="Retrieve detailed opportunity history by ID",
)
def get_history(
    history_id: int,
    db: Session = Depends(get_db),
):
    hist = db.query(OpportunityHistories).get(history_id)
    if not hist:
        raise HTTPException(status_code=404, detail="History not found")

    user = db.query(Users).get(hist.user_id)
    if not user:
        raise HTTPException(status_code=500, detail="User data missing")

    return OpportunityHistorySchema(
        id=hist.id,
        opportunity_id=hist.opportunity_id,
        user=UserInfoSchema.from_attributes(user),
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

    hist.opportunity_id = data.opportunity_id
    hist.user_id = data.user_id
    hist.comment = data.comment
    hist.status = data.status
    db.commit()
    db.refresh(hist)

    user = db.query(Users).get(hist.user_id)
    return OpportunityHistorySchema(
        id=hist.id,
        opportunity_id=hist.opportunity_id,
        user=UserInfoSchema.from_attributes(user),
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
