from schemas.event import *
from database import get_db
from models import UpComingEvents
from sqlalchemy.orm import Session
from datetime import date as DateType
from fastapi.responses import JSONResponse
from fastapi import APIRouter, Depends, HTTPException, status

router = APIRouter(
    tags=["events"],
    responses={404: {"description": "Not found"}},
)

@router.get(
    "/events",
    response_model=EventsListResponse,
    summary="List all upcoming events",
)
def get_events(db: Session = Depends(get_db)):
    """
    Fetch all upcoming events, ordered by date.
    """
    events = db.query(UpComingEvents).order_by(UpComingEvents.date).all()
    return EventsListResponse(
        message="Fetched all upcoming events.",
        events=events  # Pydantic will read attributes via from_attributes
    )

@router.post(
    "/event/add",
    response_model=EventResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new upcoming event",
)
def add_event(event_in: EventCreate, db: Session = Depends(get_db)):
    """
    Create a new event. Prevents duplicates on the same date+description.
    """
    duplicate = (
        db.query(UpComingEvents)
        .filter_by(date=event_in.date, description=event_in.description)
        .first()
    )
    if duplicate:
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
        description=event_in.description
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
    summary="Retrieve a single event by ID",
)
def show_event(event_id: int, db: Session = Depends(get_db)):
    """
    Fetch one event by its primary key.
    """
    event = db.get(UpComingEvents, event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "not_found",
                "message": f"No event found with ID {event_id}."
            },
        )
    return EventResponse(
        message="Event fetched successfully.",
        event=event
    )

@router.put(
    "/event/{event_id}/update",
    response_model=EventResponse,
    summary="Update an existing event",
)
def update_event(
    event_id: int,
    event_in: EventUpdate,
    db: Session = Depends(get_db)
):
    """
    Update one or more fields of an event.
    """
    event = db.get(UpComingEvents, event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "not_found",
                "message": f"No event found with ID {event_id}."
            },
        )

    # Only apply fields present in the request
    update_data = event_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(event, field, value)

    db.commit()
    db.refresh(event)

    return EventResponse(
        message="Event updated successfully.",
        event=event
    )

@router.delete(
    "/event/{event_id}/delete",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an event by ID",
)
def delete_event(event_id: int, db: Session = Depends(get_db)):
    """
    Permanently remove an event record.
    """
    event = db.get(UpComingEvents, event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "not_found",
                "message": f"No event found with ID {event_id}."
            },
        )

    db.delete(event)
    db.commit()
    # 204 No Content
    return JSONResponse(status_code=status.HTTP_204_NO_CONTENT)
