import os
import datetime
from io import BytesIO
from typing import Optional

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    File,
    UploadFile,
    Form,
    Request,
    Query,
    status,
)
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import asc, desc, func
from PIL import Image, UnidentifiedImageError

from database import get_db
from models import Opportunities, Users
from schemas.opportunity import (
    CreateOpportunitySchema,
    OpportunitySchema,
    OpportunityListResponse,
    OpportunityUserSchema,
)
from routers.auth import get_current_user

router = APIRouter(
    prefix="/opportunities",
    tags=["opportunities"],
    dependencies=[Depends(get_current_user)],
)

# ensure upload folder
UPLOAD_DIR = os.path.join(os.getcwd(), "uploads", "opportunities")
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.get(
    "/",
    response_model=OpportunityListResponse,
    summary="Retrieve paginated list of opportunities with nested user data",
)
def list_opportunities(
    request: Request,
    *,
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Filter by title or description"),
    sort_by: str = Query(
        "created_at",
        regex="^(id|date|created_at)$",
        description="Field to sort by",
    ),
    order: str = Query(
        "desc", regex="^(asc|desc)$", description="Sort direction"
    ),
) -> OpportunityListResponse:
    # 1) Total count
    total = db.query(func.count(Opportunities.id)).scalar()

    # 2) Query with optional search
    q = db.query(Opportunities)
    if search:
        term = f"%{search.strip()}%"
        q = q.filter(
            Opportunities.title.ilike(term)
            | Opportunities.description.ilike(term)
        )

    # 3) Ordering
    direction = asc if order == "asc" else desc
    q = q.order_by(direction(getattr(Opportunities, sort_by)))

    # 4) Pagination
    offset = (page - 1) * page_size
    raw = q.offset(offset).limit(page_size).all()
    if not raw and page != 1:
        raise HTTPException(status_code=404, detail="Page out of range")

    # 5) Build items
    base = str(request.base_url).rstrip("/")
    items = []
    for op in raw:
        # nested user lookup
        user = db.query(Users).get(op.user_id)
        if not user:
            raise HTTPException(
                status_code=404,
                detail={"error": "user_not_found", "message": f"User {op.user_id} not found"},
            )
        photo_url = f"{base}{op.photo}"
        items.append(
            OpportunitySchema(
                id=op.id,
                photo=photo_url,
                title=op.title,
                description=op.description,
                date=op.date,
                status=op.status,
                link=op.link,
                created_at=op.created_at,
                updated_at=op.updated_at,
                user=OpportunityUserSchema.from_attributes(user),
            )
        )

    # 6) Navigation URLs
    def make_url(p: int) -> str:
        return str(request.url.include_query_params(page=p, page_size=page_size))

    prev_page = make_url(page - 1) if page > 1 else None
    next_page = make_url(page + 1) if offset + len(items) < total else None

    return OpportunityListResponse(
        total=total,
        page=page,
        page_size=page_size,
        next_page=next_page,
        prev_page=prev_page,
        items=items,
    )

@router.post(
    "/add",
    status_code=status.HTTP_201_CREATED,
    summary="Create a new opportunity with image upload and auto-crop",
)
async def add_opportunity(
    request: Request,
    title: str = Form(..., description="Opportunity title"),
    description: str = Form(..., description="Opportunity description"),
    date: datetime.date = Form(..., description="Date of the opportunity"),
    user_id: int = Form(..., description="ID of the user posting"),
    status: Optional[str] = Form(None, description="Opportunity status"),
    link: Optional[str] = Form(None, description="External link"),
    photo: UploadFile = File(..., description="Image file for the opportunity"),
    db: Session = Depends(get_db),
):
    # 1) Validate metadata
    data = CreateOpportunitySchema(
        title=title,
        description=description,
        date=date,
        user_id=user_id,
        status=status,
        link=link,
    )

    # 2) Duplicate check
    if (
        db.query(Opportunities)
        .filter(
            Opportunities.title == data.title,
            Opportunities.date == data.date,
            Opportunities.user_id == data.user_id,
        )
        .first()
    ):
        raise HTTPException(
            status_code=400,
            detail={"error": "opportunity_exists", "message": "Duplicate opportunity"},
        )

    # 3) Filename
    slug = "".join(c for c in data.title.lower().replace(" ", "_") if c.isalnum() or c == "_")
    date_str = data.date.strftime("%Y%m%d")
    ext = os.path.splitext(photo.filename)[1] or ".jpg"
    filename = f"{slug}_{date_str}{ext}"
    filepath = os.path.join(UPLOAD_DIR, filename)

    # 4) Validate and crop in-memory
    contents = await photo.read()
    buf = BytesIO(contents)
    try:
        img = Image.open(buf)
        img = img.convert("RGB")
        img = img.resize((1270, 720), Image.LANCZOS)
    except UnidentifiedImageError:
        raise HTTPException(400, detail="Invalid image file")

    # 5) Save to disk
    img.save(filepath, quality=85)

    # 6) Persist
    new_op = Opportunities(
        title=data.title,
        description=data.description,
        date=data.date,
        user_id=data.user_id,
        status=data.status,
        link=data.link,
        photo=f"/uploads/opportunities/{filename}",
    )
    db.add(new_op)
    db.commit()
    db.refresh(new_op)

    # 7) Build URLs & nested user
    base = str(request.base_url).rstrip("/")
    photo_url = f"{base}{new_op.photo}"
    user = db.query(Users).get(new_op.user_id)

    return JSONResponse(
        status_code=201,
        content={
            "status": "success",
            "message": "Opportunity created",
            "opportunity": OpportunitySchema(
                id=new_op.id,
                photo=photo_url,
                title=new_op.title,
                description=new_op.description,
                date=new_op.date,
                status=new_op.status,
                link=new_op.link,
                created_at=new_op.created_at,
                updated_at=new_op.updated_at,
                user=OpportunityUserSchema.from_attributes(user),
            ).model_dump(),
        },
    )

@router.get(
    "/{op_id}",
    response_model=OpportunitySchema,
    summary="Retrieve detailed information for a single opportunity by ID",
)
def get_opportunity(
    op_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    # 1) Fetch
    op = db.query(Opportunities).get(op_id)
    if not op:
        raise HTTPException(404, detail="Opportunity not found")

    # 2) Nested user
    user = db.query(Users).get(op.user_id)
    if not user:
        raise HTTPException(404, detail="User not found")

    # 3) Build photo URL
    base = str(request.base_url).rstrip("/")
    photo_url = f"{base}{op.photo}"

    return OpportunitySchema(
        id=op.id,
        photo=photo_url,
        title=op.title,
        description=op.description,
        date=op.date,
        status=op.status,
        link=op.link,
        created_at=op.created_at,
        updated_at=op.updated_at,
        user=OpportunityUserSchema.from_attributes(user),
    )

@router.put(
    "/{op_id}/update",
    response_model=OpportunitySchema,
    summary="Update an existing opportunity by ID",
)
async def update_opportunity(
    op_id: int,
    request: Request,
    title: str = Form(..., description="Updated title"),
    description: str = Form(..., description="Updated description"),
    date: datetime.date = Form(..., description="Updated date"),
    status: Optional[str] = Form(None),
    link: Optional[str] = Form(None),
    photo: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
):
    # 1) Fetch
    op = db.query(Opportunities).get(op_id)
    if not op:
        raise HTTPException(404, detail="Opportunity not found")

    # 2) Validate metadata
    data = CreateOpportunitySchema(
        title=title,
        description=description,
        date=date,
        user_id=op.user_id,
        status=status,
        link=link,
    )

    # 3) Prevent duplicate
    dup = (
        db.query(Opportunities)
        .filter(
            Opportunities.id != op_id,
            Opportunities.title == data.title,
            Opportunities.date == data.date,
            Opportunities.user_id == op.user_id,
        )
        .first()
    )
    if dup:
        raise HTTPException(400, detail="Duplicate opportunity")

    # 4) Update fields
    op.title = data.title
    op.description = data.description
    op.date = data.date
    op.status = data.status
    op.link = data.link

    # 5) Handle new photo
    if photo:
        old = os.path.join(os.getcwd(), op.photo.lstrip("/"))
        if os.path.isfile(old):
            os.remove(old)

        slug = "".join(c for c in data.title.lower().replace(" ", "_") if c.isalnum() or c == "_")
        date_str = data.date.strftime("%Y%m%d")
        ext = os.path.splitext(photo.filename)[1] or ".jpg"
        filename = f"{slug}_{date_str}{ext}"
        fp = os.path.join(UPLOAD_DIR, filename)

        buf = BytesIO(await photo.read())
        try:
            img = Image.open(buf)
            img = img.convert("RGB")
            img = img.resize((1270, 720), Image.LANCZOS)
            img.save(fp, quality=85)
        except UnidentifiedImageError:
            raise HTTPException(400, detail="Invalid image")

        op.photo = f"/uploads/opportunities/{filename}"

    db.commit()
    db.refresh(op)

    # 6) Nested user & photo URL
    user = db.query(Users).get(op.user_id)
    base = str(request.base_url).rstrip("/")
    photo_url = f"{base}{op.photo}"

    return OpportunitySchema(
        id=op.id,
        photo=photo_url,
        title=op.title,
        description=op.description,
        date=op.date,
        status=op.status,
        link=op.link,
        created_at=op.created_at,
        updated_at=op.updated_at,
        user=OpportunityUserSchema.from_attributes(user),
    )

@router.delete(
    "/{op_id}/delete",
    status_code=status.HTTP_200_OK,
    summary="Delete a specific opportunity and its image",
)
def delete_opportunity(
    op_id: int,
    db: Session = Depends(get_db),
):
    # 1) Fetch
    op = db.query(Opportunities).get(op_id)
    if not op:
        raise HTTPException(404, detail="Opportunity not found")

    # 2) Remove image file
    path = os.path.join(os.getcwd(), op.photo.lstrip("/"))
    if os.path.isfile(path):
        os.remove(path)

    # 3) Delete record
    db.delete(op)
    db.commit()

    return JSONResponse({"status": "success", "message": f"Opportunity {op_id} deleted."})
