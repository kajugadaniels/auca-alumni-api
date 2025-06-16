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

@router.get(
    "/event/{event_id}",
    response_model=EventResponse,
    summary="Get a single upcoming event by ID"
)
def show_event(event_id: int, db: Session = Depends(get_db)):
    event = db.query(UpComingEvents).get(event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "not_found", "message": f"No event found with ID {event_id}."},
        )
    return EventResponse(message="Event fetched successfully.", event=event)

@router.put(
    "/event/{event_id}/update",
    response_model=EventResponse,
    summary="Update an existing upcoming event"
)
def update_event(event_id: int, event_in: EventUpdate, db: Session = Depends(get_db)):
    event = db.query(UpComingEvents).get(event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "not_found", "message": f"No event found with ID {event_id}."},
        )

    for field, value in event_in.dict(exclude_unset=True).items():
        setattr(event, field, value)
    db.commit()
    db.refresh(event)
    return EventResponse(message="Event updated successfully.", event=event)

@router.delete(
    "/event/{event_id}/delete",
    response_model=None,
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an upcoming event"
)
def delete_event(event_id: int, db: Session = Depends(get_db)):
    event = db.query(UpComingEvents).get(event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "not_found", "message": f"No event found with ID {event_id}."},
        )
    db.delete(event)
    db.commit()
    # 204: no content
    return JSONResponse(status_code=status.HTTP_204_NO_CONTENT)