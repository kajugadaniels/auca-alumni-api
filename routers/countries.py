"""
Router for public access to countries list.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import func

from database import get_db
from models import Countries
from schemas.country import CountrySchema

router = APIRouter()

@router.get(
    "/countries",
    response_model=list[CountrySchema],
    summary="Retrieve list of all countries",
)
def list_countries(
    request: Request,
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(100, ge=1, le=1000, description="Maximum items per page"),
):
    """
    Returns a paginated list of countries. Include total count in headers for client convenience.
    """
    # count total countries
    total = db.query(func.count(Countries.id)).scalar()

    # calculate pagination
    offset = (page - 1) * page_size
    items = db.query(Countries).order_by(Countries.name).offset(offset).limit(page_size).all()

    if not items and page != 1:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Page out of range")

    # set custom headers
    headers = {
        "X-Total-Count": str(total),
        "X-Page": str(page),
        "X-Page-Size": str(page_size),
    }

    return JSONResponse(content=[CountrySchema.from_orm(c).model_dump() for c in items], headers=headers)