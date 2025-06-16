from models import *
from datetime import date
from database import get_db
from schemas.event import *
from sqlalchemy.orm import Session
from fastapi.responses import JSONResponse
from fastapi import APIRouter, Depends, HTTPException, status

router = APIRouter()

@router.get("/events", response_model=EventsListResponse, summary="Get all upcoming events")
def get_events(db: Session = Depends(get_db)):
    events = db.query(UpComingEvents).order_by(UpComingEvents.date).all()
    return EventsListResponse(
        message="Fetched all upcoming events.",
        events=events
    )

