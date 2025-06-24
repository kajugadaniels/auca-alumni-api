import os
from io import BytesIO
import datetime
from typing import Optional

from fastapi import (
    APIRouter, Depends, HTTPException,
    File, UploadFile, Form, Request,
    Query, status
)
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import asc, desc, func
from PIL import Image, UnidentifiedImageError

from database import get_db
from models import ExecutiveComittes
from schemas.executive_committees import (
    CreateExecutiveCommitteeSchema,
    ExecutiveCommitteeSchema,
    ExecutiveCommitteeListResponse,
)
from routers.auth import get_current_user

router = APIRouter(
    prefix="/executive-committees",
    tags=["executive-committees"],
    dependencies=[Depends(get_current_user)],
)

# Upload directory
UPLOAD_DIR = os.path.join(os.getcwd(), "uploads", "executive_committees")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ------------------------------------------------------------------------
# GET /executive-committees/
# ------------------------------------------------------------------------
@router.get(
    "/",
    response_model=ExecutiveCommitteeListResponse,
    summary="Get paginated list of executive committee members",
)
def list_committees(
    request: Request,
    *,
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Filter by name or position"),
    sort_by: str = Query(
        "created_at",
        regex="^(id|name|position|created_at)$",
        description="Field to sort by"
    ),
    order: str = Query("desc", regex="^(asc|desc)$", description="Sort direction"),
) -> ExecutiveCommitteeListResponse:
    total = db.query(func.count(ExecutiveComittes.id)).scalar()
    q = db.query(ExecutiveComittes)
    if search:
        term = f"%{search.strip()}%"
        q = q.filter(
            ExecutiveComittes.name.ilike(term)
            | ExecutiveComittes.position.ilike(term)
        )
    direction = asc if order == "asc" else desc
    q = q.order_by(direction(getattr(ExecutiveComittes, sort_by)))
    offset = (page - 1) * page_size
    raw = q.offset(offset).limit(page_size).all()
    if not raw and page != 1:
        raise HTTPException(status_code=404, detail="Page out of range")

    base = str(request.base_url).rstrip("/")
    items = [
        ExecutiveCommitteeSchema(
            **{
                **member.__dict__,
                "photo": f"{base}{member.photo}"
            }
        )
        for member in raw
    ]

    def make_url(p: int) -> str:
        return str(request.url.include_query_params(page=p, page_size=page_size))

    return ExecutiveCommitteeListResponse(
        total=total,
        page=page,
        page_size=page_size,
        next_page=make_url(page+1) if offset + len(items) < total else None,
        prev_page=make_url(page-1) if page > 1 else None,
        items=items,
    )

@router.post(
    "/add",
    response_model=ExecutiveCommitteeSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Add a new executive committee member",
)
async def add_committee_member(
    request: Request,
    name: str = Form(..., description="Full name"),
    position: str = Form(..., description="Position/title"),
    photo: UploadFile = File(..., description="Member photo"),
    db: Session = Depends(get_db),
):
    # 1) Validate payload
    schema = CreateExecutiveCommitteeSchema(
        name=name, position=position, photo=await photo.read()
    )

    # 2) Prevent duplicate name+position
    if db.query(ExecutiveComittes).filter_by(
        name=schema.name, position=schema.position
    ).first():
        raise HTTPException(
            status_code=400,
            detail={"error": "duplicate_member", "message": "Member already exists."},
        )

    # 3) Process image
    ext = os.path.splitext(photo.filename)[1] or ".jpg"
    slug = "_".join(schema.name.lower().split())
    filename = f"{slug}{ext}"
    filepath = os.path.join(UPLOAD_DIR, filename)

    buf = BytesIO(schema.photo)
    try:
        img = Image.open(buf).convert("RGB").resize((1270, 720), Image.LANCZOS)
        img.save(filepath, quality=85)
    except UnidentifiedImageError:
        raise HTTPException(status_code=400, detail="Invalid image file")

    # 4) Persist
    member = ExecutiveComittes(
        name=schema.name,
        position=schema.position,
        photo=f"/uploads/executive_committees/{filename}",
    )
    db.add(member)
    db.commit()
    db.refresh(member)

    # 5) Return response
    base = str(request.base_url).rstrip("/")
    return ExecutiveCommitteeSchema(
        **{
            **member.__dict__,
            "photo": f"{base}{member.photo}"
        }
    )

@router.get(
    "/{member_id}",
    response_model=ExecutiveCommitteeSchema,
    summary="Get detailed executive committee member by ID",
)
def get_committee_member(
    member_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    member = db.query(ExecutiveComittes).get(member_id)
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    base = str(request.base_url).rstrip("/")
    return ExecutiveCommitteeSchema(
        **{
            **member.__dict__,
            "photo": f"{base}{member.photo}"
        }
    )

@router.put(
    "/{member_id}/update",
    response_model=ExecutiveCommitteeSchema,
    summary="Update an executive committee member by ID",
)
async def update_committee_member(
    member_id: int,
    request: Request,
    name: str = Form(..., description="Updated full name"),
    position: str = Form(..., description="Updated position/title"),
    photo: Optional[UploadFile] = File(None, description="New photo (optional)"),
    db: Session = Depends(get_db),
):
    member = db.query(ExecutiveComittes).get(member_id)
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    # 1) Validate new values
    schema = CreateExecutiveCommitteeSchema(
        name=name,
        position=position,
        photo=(await photo.read()) if photo else b"",
    )

    # 2) Duplicate check
    dup = db.query(ExecutiveComittes).filter(
        ExecutiveComittes.id != member_id,
        ExecutiveComittes.name == schema.name,
        ExecutiveComittes.position == schema.position
    ).first()
    if dup:
        raise HTTPException(status_code=400, detail="Another member with same name & position exists")

    member.name = schema.name
    member.position = schema.position

    # 3) Optional photo replace
    if photo:
        old = os.path.join(os.getcwd(), member.photo.lstrip("/"))
        if os.path.isfile(old):
            os.remove(old)
        ext = os.path.splitext(photo.filename)[1] or ".jpg"
        slug = "_".join(schema.name.lower().split())
        filename = f"{slug}{ext}"
        fp = os.path.join(UPLOAD_DIR, filename)

        buf = BytesIO(schema.photo)
        try:
            img = Image.open(buf).convert("RGB").resize((1270, 720), Image.LANCZOS)
            img.save(fp, quality=85)
        except UnidentifiedImageError:
            raise HTTPException(status_code=400, detail="Invalid image file")

        member.photo = f"/uploads/executive_committees/{filename}"

    db.commit()
    db.refresh(member)

    base = str(request.base_url).rstrip("/")
    return ExecutiveCommitteeSchema(
        **{
            **member.__dict__,
            "photo": f"{base}{member.photo}"
        }
    )

@router.delete(
    "/{member_id}/delete",
    status_code=status.HTTP_200_OK,
    summary="Delete an executive committee member and their photo",
)
def delete_committee_member(
    member_id: int,
    db: Session = Depends(get_db),
):
    member = db.query(ExecutiveComittes).get(member_id)
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    # remove photo file
    path = os.path.join(os.getcwd(), member.photo.lstrip("/"))
    if os.path.isfile(path):
        os.remove(path)

    db.delete(member)
    db.commit()

    return JSONResponse({"status":"success","message":f"Member {member_id} deleted."})
