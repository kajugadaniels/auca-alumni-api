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

@router.post(
    "/event/add", 
    response_model=EventResponse, 
    status_code=status.HTTP_201_CREATED,
    summary="Create a new upcoming event"
)
def add_event(event_in: EventCreate, db: Session = Depends(get_db)):
    # Prevent duplicate event on same date+description
    exists = (
        db.query(UpComingEvents)
        .filter_by(date=event_in.date, description=event_in.description)
        .first()
    )
    if exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "event_exists",
                "message": "An event with this date and description already exists."
            },
        )

    new_event = UpComingEvents(
        photo=event_in.photo,
        date=event_in.date,
        description=event_in.description,
    )
    db.add(new_event)
    db.commit()
    db.refresh(new_event)
    return EventResponse(
        message="Event created successfully.",
        event=new_event
    )