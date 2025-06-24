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

# Directory for opportunity images
UPLOAD_DIR = os.path.join(os.getcwd(), "uploads", "opportunities")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ------------------------------------------------------------------------
# GET /opportunities
# ------------------------------------------------------------------------
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

    # 2) Base query + optional search
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

    # 5) Build response items
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
                **{
                    **op.__dict__,
                    "photo": photo_url,
                    "user": OpportunityUserSchema.model_validate(user),
                }
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
    summary="Create a new opportunity with image upload and auto‐crop",
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
    # 1) Validate payload
    data = CreateOpportunitySchema(
        title=title,
        description=description,
        date=date,
        user_id=user_id,
        status=status,
        link=link,
    )

    # 2) Prevent duplicate
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

    # 3) Build filename
    slug = "".join(c for c in data.title.lower().replace(" ", "_") if c.isalnum() or c == "_")
    date_str = data.date.strftime("%Y%m%d")
    ext = os.path.splitext(photo.filename)[1] or ".jpg"
    filename = f"{slug}_{date_str}{ext}"
    filepath = os.path.join(UPLOAD_DIR, filename)

    # 4) Validate and resize in-memory
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

    # 6) Persist record
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

    # 7) Build response
    base = str(request.base_url).rstrip("/")
    photo_url = f"{base}{new_op.photo}"
    user = db.query(Users).get(new_op.user_id)

    return JSONResponse(
        status_code=201,
        content={
            "status": "success",
            "message": "Opportunity created successfully",
            "opportunity": OpportunitySchema(
                **{
                    **new_op.__dict__,
                    "photo": photo_url,
                    "user": OpportunityUserSchema.model_validate(user),
                }
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
    # 1) Fetch record
    op = db.query(Opportunities).get(op_id)
    if not op:
        raise HTTPException(status_code=404, detail="Opportunity not found")

    # 2) Fetch user
    user = db.query(Users).get(op.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # 3) Build photo URL
    base = str(request.base_url).rstrip("/")
    photo_url = f"{base}{op.photo}"

    return OpportunitySchema(
        **{
            **op.__dict__,
            "photo": photo_url,
            "user": OpportunityUserSchema.model_validate(user),
        }
    )

