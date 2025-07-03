import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import desc

from database import get_db
from models import Discussions
from schemas.discussion import (
    CreateDiscussionSchema,
    DiscussionSchema,
    DiscussionListResponse,
)
from routers.auth import get_current_user

router = APIRouter(
    tags=["discussions"],
    prefix="/discussions",
    dependencies=[Depends(get_current_user)],  # all routes require auth
)


# ------------------------------------------------------
# GET /discussions – return all messages (latest first)
# ------------------------------------------------------
@router.get(
    "/",
    response_model=DiscussionListResponse,
    summary="Retrieve all discussion messages ordered by latest first",
)
def list_discussions(
    db: Session = Depends(get_db),
) -> DiscussionListResponse:
    msgs: List[Discussions] = (
        db.query(Discussions).order_by(desc(Discussions.created_at)).all()
    )
    return DiscussionListResponse(
        total=len(msgs),
        items=msgs,
    )


# ------------------------------------------------------
# POST /discussions/send – create a new message
# ------------------------------------------------------
@router.post(
    "/send",
    response_model=DiscussionSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Send (create) a new discussion message",
)
def send_message(
    payload: CreateDiscussionSchema,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
) -> DiscussionSchema:
    """
    Creates a new message. The user_id is always taken from the authenticated user,
    ignoring any user_id in the inbound payload.
    """
    new_msg = Discussions(
        user_id=current_user.id,
        message=payload.message.strip(),
        created_at=datetime.datetime.utcnow(),
    )
    db.add(new_msg)
    db.commit()
    db.refresh(new_msg)
    return new_msg
