from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from database import get_db
from models import UpComingEvents
from schemas.event import (
    EventCreate,
    EventUpdate,
    EventResponse,
    EventListResponse,
)

router = APIRouter(prefix="/events", tags=["events"])

@router.get("/", response_model=EventListResponse, summary="List all upcoming events")
def get_events(db: Session = Depends(get_db)):
    """
    Retrieve all upcoming events.
    """
    events = db.query(UpComingEvents).order_by(UpComingEvents.date).all()
    return {
        "status": "success",
        "message": f"Retrieved {len(events)} event(s).",
        "data": events,
    }


@router.post(
    "/", 
    response_model=EventResponse, 
    status_code=status.HTTP_201_CREATED,
    summary="Create a new upcoming event"
)
def add_event(event_in: EventCreate, db: Session = Depends(get_db)):
    """
    Add a new upcoming event. Validates payload via Pydantic.
    """
    new_event = UpComingEvents(
        photo=str(event_in.photo),
        date=event_in.date,
        description=event_in.description,
    )
    db.add(new_event)
    db.commit()
    db.refresh(new_event)
    return new_event


@router.get(
    "/{event_id}",
    response_model=EventResponse,
    summary="Fetch a single event by ID"
)
def show_event(event_id: int, db: Session = Depends(get_db)):
    """
    Get details of a single event.
    """
    event = db.query(UpComingEvents).get(event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"status": "error", "message": f"Event #{event_id} not found"}
        )
    return event


@router.put(
    "/{event_id}",
    response_model=EventResponse,
    summary="Update an existing event"
)
def update_event(
    event_id: int,
    event_in: EventUpdate,
    db: Session = Depends(get_db),
):
    """
    Update an event completely (all fields optional).
    """
    event = db.query(UpComingEvents).get(event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"status": "error", "message": f"Event #{event_id} not found"}
        )
    # Apply updates
    for field, value in event_in.model_dump(exclude_unset=True).items():
        setattr(event, field, value)
    db.commit()
    db.refresh(event)
    return event


@router.delete(
    "/{event_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete an event"
)
def delete_event(event_id: int, db: Session = Depends(get_db)):
    """
    Remove an event by ID.
    """
    event = db.query(UpComingEvents).get(event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"status": "error", "message": f"Event #{event_id} not found"}
        )
    db.delete(event)
    db.commit()
    return {"status": "success", "message": f"Event #{event_id} deleted successfully"}
