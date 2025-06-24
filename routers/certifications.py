import os
from io import BytesIO
import datetime
from typing import Optional

from fastapi import (
    APIRouter, Depends, HTTPException,
    Query, Request, Form, File, UploadFile, status
)
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import asc, desc, func
from PIL import Image, UnidentifiedImageError

from database import get_db
from models import Certifications, Users
from schemas.certification import (
    CreateCertificationSchema,
    CertificationSchema,
    CertificationListResponse,
    UserNestedSchema,
)
from routers.auth import get_current_user

router = APIRouter(
    prefix="/certifications",
    tags=["certifications"],
    dependencies=[Depends(get_current_user)],
)

# Ensure upload directory
UPLOAD_DIR = os.path.join(os.getcwd(), "uploads", "certifications")
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.get(
    "/",
    response_model=CertificationListResponse,
    summary="List certifications with pagination, search, and sorting",
)
def list_certifications(
    request: Request,
    *,
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Filter by certificate name or type"),
    sort_by: str = Query(
        "created_at",
        regex="^(id|year|created_at)$",
        description="Field to sort by"
    ),
    order: str = Query("desc", regex="^(asc|desc)$", description="Sort direction"),
) -> CertificationListResponse:
    # 1) Total count
    total = db.query(func.count(Certifications.id)).scalar()

    # 2) Base query + optional search
    q = db.query(Certifications)
    if search:
        term = f"%{search.strip()}%"
        q = q.filter(
            Certifications.certificate_name.ilike(term)
            | Certifications.type.ilike(term)
        )

    # 3) Ordering
    direction = asc if order == "asc" else desc
    q = q.order_by(direction(getattr(Certifications, sort_by)))

    # 4) Pagination
    offset = (page - 1) * page_size
    raw = q.offset(offset).limit(page_size).all()
    if not raw and page != 1:
        raise HTTPException(status_code=404, detail="Page out of range")

    # 5) Build items with nested user and full image URL
    base = str(request.base_url).rstrip("/")
    items = []
    for cert in raw:
        user = db.query(Users).get(cert.user_id)
        if not user:
            raise HTTPException(
                status_code=404,
                detail={"error": "user_not_found", "message": f"User {cert.user_id} not found"},
            )
        items.append(
            CertificationSchema(
                id=cert.id,
                user=UserNestedSchema.model_validate(user),
                certificate_name=cert.certificate_name,
                year=cert.year,
                type=cert.type,
                description=cert.description,
                image=f"{base}{cert.image}",
                created_at=cert.created_at,
                updated_at=cert.updated_at,
            )
        )

    def make_url(p: int) -> str:
        return str(request.url.include_query_params(page=p, page_size=page_size))

    return CertificationListResponse(
        total=total,
        page=page,
        page_size=page_size,
        next_page=make_url(page+1) if offset + len(items) < total else None,
        prev_page=make_url(page-1) if page > 1 else None,
        items=items,
    )

@router.post(
    "/add",
    response_model=CertificationSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Add a new certification with image upload",
)
async def add_certification(
    request: Request,
    user_id: int = Form(..., description="ID of the user"),
    certificate_name: str = Form(..., description="Name of the certification"),
    year: int = Form(..., description="Year obtained"),
    type: str = Form(..., description="Certification type"),
    description: str = Form(..., description="Description"),
    image: UploadFile = File(..., description="Certificate image file"),
    db: Session = Depends(get_db),
):
    # 1) Validate payload
    schema = CreateCertificationSchema(
        user_id=user_id,
        certificate_name=certificate_name,
        year=year,
        type=type,
        description=description,
        image=await image.read()
    )

    # 2) Verify user exists
    user = db.query(Users).get(schema.user_id)
    if not user:
        raise HTTPException(status_code=400, detail="User not found")

    # 3) Prevent duplicates for same user/year/name
    if db.query(Certifications).filter_by(
        user_id=schema.user_id,
        certificate_name=schema.certificate_name,
        year=schema.year
    ).first():
        raise HTTPException(status_code=400, detail="Duplicate certification record")

    # 4) Process image
    ext = os.path.splitext(image.filename)[1] or ".jpg"
    slug = "_".join(schema.certificate_name.lower().split())
    filename = f"{slug}_{schema.year}{ext}"
    filepath = os.path.join(UPLOAD_DIR, filename)

    buf = BytesIO(schema.image)
    try:
        img = Image.open(buf).convert("RGB").resize((1270, 720), Image.LANCZOS)
        img.save(filepath, quality=85)
    except UnidentifiedImageError:
        raise HTTPException(status_code=400, detail="Invalid image file")

    # 5) Persist
    cert = Certifications(
        user_id=schema.user_id,
        certificate_name=schema.certificate_name,
        year=schema.year,
        type=schema.type,
        description=schema.description,
        image=f"/uploads/certifications/{filename}",
    )
    db.add(cert)
    db.commit()
    db.refresh(cert)

    base = str(request.base_url).rstrip("/")
    return CertificationSchema(
        id=cert.id,
        user=UserNestedSchema.model_validate(user),
        certificate_name=cert.certificate_name,
        year=cert.year,
        type=cert.type,
        description=cert.description,
        image=f"{base}{cert.image}",
        created_at=cert.created_at,
        updated_at=cert.updated_at,
    )

@router.get(
    "/{cert_id}",
    response_model=CertificationSchema,
    summary="Get a single certification by ID",
)
def get_certification(
    cert_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    cert = db.query(Certifications).get(cert_id)
    if not cert:
        raise HTTPException(status_code=404, detail="Certification not found")
    user = db.query(Users).get(cert.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    base = str(request.base_url).rstrip("/")
    return CertificationSchema(
        id=cert.id,
        user=UserNestedSchema.model_validate(user),
        certificate_name=cert.certificate_name,
        year=cert.year,
        type=cert.type,
        description=cert.description,
        image=f"{base}{cert.image}",
        created_at=cert.created_at,
        updated_at=cert.updated_at,
    )

