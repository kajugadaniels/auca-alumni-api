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
from fastapi.encoders import jsonable_encoder

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

# ------------------------------------------------------------------------
# POST /personal-information/add: create new personal info with photo
# ------------------------------------------------------------------------
@router.post(
    "/add",
    status_code=status.HTTP_201_CREATED,
    summary="Create a new personal information record with photo upload and auto-crop",
)
async def add_personal_information(
    request: Request,
    bio: str = Form(...),
    current_employer: Optional[str] = Form(None),
    self_employed: Optional[str] = Form(None),
    latest_education_level: Optional[str] = Form(None),
    address: str = Form(...),
    profession_id: Optional[int] = Form(None),
    user_id: int = Form(...),
    dob: Optional[datetime.date] = Form(None),
    start_date: Optional[datetime.date] = Form(None),
    end_date: Optional[datetime.date] = Form(None),
    faculty_id: Optional[int] = Form(None),
    country_id: Optional[str] = Form(None),
    department: Optional[str] = Form(None),
    gender: bool = Form(...),
    status_info: Optional[str] = Form(None, alias="status", description="Current status"),
    photo: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    Creates:
    - Validates via CreatePersonalInformationSchema
    - Crops & saves photo (1270×720) in-memory
    - Persists record and returns nested user data
    """
    # 1) Validate inputs
    data = CreatePersonalInformationSchema(
        bio=bio,
        current_employer=current_employer,
        self_employed=self_employed,
        latest_education_level=latest_education_level,
        address=address,
        profession_id=profession_id,
        user_id=user_id,
        dob=dob,
        start_date=start_date,
        end_date=end_date,
        faculty_id=faculty_id,
        country_id=country_id,
        department=department,
        gender=gender,
        status=status_info,
    )

    # 2) Verify user exists
    user = db.query(Users).get(data.user_id)
    if not user:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid user_id")

    # 3) Build filename
    slug = f"user_{data.user_id}_{int(datetime.datetime.utcnow().timestamp())}"
    ext = os.path.splitext(photo.filename)[1] or ".jpg"
    filename = f"{slug}{ext}"
    filepath = os.path.join(UPLOAD_DIR, filename)

    # 4) Read & crop in-memory
    contents = await photo.read()
    buf = BytesIO(contents)
    try:
        img = Image.open(buf)
        img = img.convert("RGB")
        img = img.resize((1270, 720), Image.LANCZOS)
    except UnidentifiedImageError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid image upload")

    img.save(filepath, quality=85)

    # 5) Persist
    pi = PersonalInformation(
        photo=f"/uploads/personal_information/{filename}",
        bio=data.bio,
        current_employer=data.current_employer,
        self_employed=data.self_employed,
        latest_education_level=data.latest_education_level,
        address=data.address,
        profession_id=data.profession_id,
        user_id=data.user_id,
        dob=data.dob,
        start_date=data.start_date,
        end_date=data.end_date,
        faculty_id=data.faculty_id,
        country_id=data.country_id,
        department=data.department,
        gender=data.gender,
        status=data.status,
    )
    db.add(pi)
    db.commit()
    db.refresh(pi)

    # 6) Build nested schema and JSON-serializable dict
    base = str(request.base_url).rstrip("/")
    schema = PersonalInformationSchema(
        id=pi.id,
        photo=f"{base}{pi.photo}",
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
    profile_dict = schema.model_dump(mode="json")

    # 7) Return success JSON
    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={
            "status": "success",
            "message": "Personal information created successfully.",
            "profile": profile_dict,
        },
    )

# ------------------------------------------------------------------------
# PUT /personal-information/{id}/update: update a personal info record
# ------------------------------------------------------------------------
@router.put(
    "/{pi_id}/update",
    response_model=PersonalInformationSchema,
    summary="Update an existing personal information record",
)
async def update_personal_information(
    pi_id: int,
    request: Request,
    bio: str = Form(...),
    current_employer: Optional[str] = Form(None),
    self_employed: Optional[str] = Form(None),
    latest_education_level: Optional[str] = Form(None),
    address: str = Form(...),
    profession_id: Optional[int] = Form(None),
    user_id: int = Form(...),
    dob: Optional[datetime.date] = Form(None),
    start_date: Optional[datetime.date] = Form(None),
    end_date: Optional[datetime.date] = Form(None),
    faculty_id: Optional[int] = Form(None),
    country_id: Optional[str] = Form(None),
    department: Optional[str] = Form(None),
    gender: bool = Form(...),
    status: Optional[str] = Form(None),
    photo: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
):
    # 1) Fetch existing
    pi = db.query(PersonalInformation).get(pi_id)
    if not pi:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Profile not found")

    # 2) Validate
    data = CreatePersonalInformationSchema(
        bio=bio,
        current_employer=current_employer,
        self_employed=self_employed,
        latest_education_level=latest_education_level,
        address=address,
        profession_id=profession_id,
        user_id=user_id,
        dob=dob,
        start_date=start_date,
        end_date=end_date,
        faculty_id=faculty_id,
        country_id=country_id,
        department=department,
        gender=gender,
        status=status,
    )

    # 3) Verify user exists
    user = db.query(Users).get(data.user_id)
    if not user:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid user_id")

    # 4) Update fields
    for field in ["bio","current_employer","self_employed","latest_education_level",
                  "address","profession_id","user_id","dob","start_date","end_date",
                  "faculty_id","country_id","department","gender","status"]:
        setattr(pi, field, getattr(data, field))

    # 5) Optional photo replacement
    if photo:
        # remove old
        old = os.path.join(os.getcwd(), pi.photo.lstrip("/"))
        if os.path.isfile(old): os.remove(old)

        contents = await photo.read()
        buf = BytesIO(contents)
        try:
            img = Image.open(buf)
            img = img.convert("RGB")
            img = img.resize((1270,720), Image.LANCZOS)
        except UnidentifiedImageError:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid image")

        slug = f"user_{data.user_id}_{pi_id}_{int(datetime.datetime.utcnow().timestamp())}"
        ext = os.path.splitext(photo.filename)[1] or ".jpg"
        fn = f"{slug}{ext}"
        path = os.path.join(UPLOAD_DIR, fn)
        img.save(path, quality=85)
        pi.photo = f"/uploads/personal_information/{fn}"

    # 6) Commit
    db.add(pi)
    db.commit()
    db.refresh(pi)

    base = str(request.base_url).rstrip("/")
    return PersonalInformationSchema(
        id=pi.id,
        photo=f"{base}{pi.photo}",
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

# ------------------------------------------------------------------------
# DELETE /personal-information/{id}/delete: delete a profile and its photo
# ------------------------------------------------------------------------
@router.delete(
    "/{pi_id}/delete",
    status_code=status.HTTP_200_OK,
    summary="Delete a personal information record and its photo",
)
def delete_personal_information(
    pi_id: int,
    db: Session = Depends(get_db),
):
    pi = db.query(PersonalInformation).get(pi_id)
    if not pi:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Profile not found")

    # remove photo
    path = os.path.join(os.getcwd(), pi.photo.lstrip("/"))
    if os.path.isfile(path):
        try: os.remove(path)
        except: pass

    db.delete(pi)
    db.commit()
    return JSONResponse({"status": "success", "message": f"Profile {pi_id} deleted."})
