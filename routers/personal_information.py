import os
import datetime
from io import BytesIO
from typing import Optional

from fastapi import (
    APIRouter, Depends, HTTPException, status,
    UploadFile, File, Form, Request, Query
)
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import asc, desc, func
from PIL import Image, UnidentifiedImageError

from database import get_db
from models import PersonalInformation, Users
from schemas.personal_information import (
    CreatePersonalInformationSchema,
    PersonalInformationSchema,
    PersonalInformationListResponse
)
from routers.auth import get_current_user

router = APIRouter(
    prefix="/personal-information",
    tags=["personal-information"],
    dependencies=[Depends(get_current_user)],
)

# Directory for uploads
UPLOAD_DIR = os.path.join(os.getcwd(), "uploads", "personal_information")
os.makedirs(UPLOAD_DIR, exist_ok=True)


# ------------------------------------------------------------------------
# GET /personal-information: list all with pagination
# ------------------------------------------------------------------------
@router.get(
    "/",
    response_model=PersonalInformationListResponse,
    summary="Retrieve paginated personal information records with nested user data",
)
def list_personal_information(
    request: Request,
    *,
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    sort_by: str = Query("created_at", regex="^(id|created_at)$"),
    order: str = Query("desc", regex="^(asc|desc)$"),
) -> PersonalInformationListResponse:
    # 1) total count
    total = db.query(func.count(PersonalInformation.id)).scalar()

    # 2) base query
    query = db.query(PersonalInformation)

    # 3) ordering
    direction = asc if order == "asc" else desc
    query = query.order_by(direction(getattr(PersonalInformation, sort_by)))

    # 4) pagination
    offset = (page - 1) * page_size
    raws = query.offset(offset).limit(page_size).all()
    if not raws and page != 1:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Page out of range")

    # 5) build items
    base = str(request.base_url).rstrip("/")
    items = []
    for pi in raws:
        user = db.query(Users).get(pi.user_id)
        photo_url = f"{base}{pi.photo}"
        items.append(
            PersonalInformationSchema(
                id=pi.id,
                photo=photo_url,
                bio=pi.bio,
                current_employer=pi.current_employer,
                self_employed=pi.self_employed,
                latest_education_level=pi.latest_education_level,
                address=pi.address,
                profession_id=pi.profession_id,
                user=user,
                dob=pi.dob,
                start_date=pi.start_date,
                end_date=pi.end_date,
                faculty_id=pi.faculty_id,
                country_id=pi.country_id,
                department=pi.department,
                gender=pi.gender,
                status=pi.status,
                created_at=pi.created_at,
                updated_at=pi.updated_at,
            )
        )

    def make_url(p: int) -> str:
        return str(request.url.include_query_params(page=p, page_size=page_size))

    return PersonalInformationListResponse(
        total=total,
        page=page,
        page_size=page_size,
        next_page=make_url(page + 1) if offset + len(items) < total else None,
        prev_page=make_url(page - 1) if page > 1 else None,
        items=items,
    )
