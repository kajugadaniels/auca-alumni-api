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
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Filter by title or description"),
    sort_by: str = Query(
        "created_at",
        regex="^(id|date|created_at)$",
        description="Field to sort by",
    ),
    order: str = Query("desc", regex="^(asc|desc)$", description="Sort direction"),
) -> OpportunityListResponse:
    """
    Returns a paginated, sorted list of opportunities.
    If the linked user record has been deleted, a placeholder user object
    with `"N/A"` fields is returned instead of throwing 404.
    """

    # 1️⃣ base query + optional search filter
    query = db.query(Opportunities)
    if search:
        term = f"%{search.strip()}%"
        query = query.filter(
            Opportunities.title.ilike(term) | Opportunities.description.ilike(term)
        )

    # 2️⃣ total AFTER filtering
    total = query.count()

    # 3️⃣ ordering
    direction = asc if order == "asc" else desc
    query = query.order_by(direction(getattr(Opportunities, sort_by)))

    # 4️⃣ pagination
    offset = (page - 1) * page_size
    rows = query.offset(offset).limit(page_size).all()
    if not rows and page != 1:
        raise HTTPException(status_code=404, detail="Page out of range")

    # 5️⃣ build response items
    base = str(request.base_url).rstrip("/")
    items = []
    for op in rows:
        user = db.query(Users).get(op.user_id)

        # placeholder when user missing
        if not user:
            user_data = OpportunityUserSchema(
                id=0,
                email="N/A",
                first_name="N/A",
                last_name="N/A",
                phone_number="N/A",
                student_id=0,
            )
        else:
            user_data = OpportunityUserSchema.model_validate(user)

        items.append(
            OpportunitySchema(
                **{
                    **op.__dict__,
                    "photo": f"{base}{op.photo}",
                    "user": user_data,
                }
            )
        )

    # 6️⃣ nav URLs
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
    response_model=OpportunitySchema,
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
    # 1) Validate input
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
        .filter_by(
            title=data.title,
            date=data.date,
            user_id=data.user_id,
        )
        .first()
    ):
        raise HTTPException(
            status_code=400,
            detail={"error": "opportunity_exists", "message": "Duplicate opportunity"},
        )

    # 3) Build & save image
    slug = "".join(c for c in data.title.lower().replace(" ", "_") if c.isalnum() or c == "_")
    date_str = data.date.strftime("%Y%m%d")
    ext = os.path.splitext(photo.filename)[1] or ".jpg"
    filename = f"{slug}_{date_str}{ext}"
    filepath = os.path.join(UPLOAD_DIR, filename)

    contents = await photo.read()
    buf = BytesIO(contents)
    try:
        img = Image.open(buf).convert("RGB").resize((1270, 720), Image.LANCZOS)
        img.save(filepath, quality=85)
    except UnidentifiedImageError:
        raise HTTPException(400, detail="Invalid image file")

    # 4) Persist record
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

    # 5) Nested user
    user = db.query(Users).get(new_op.user_id)
    if not user:
        raise HTTPException(404, detail="User not found")

    # 6) Build and return Pydantic model
    base = str(request.base_url).rstrip("/")
    return OpportunitySchema(
        id=new_op.id,
        photo=f"{base}{new_op.photo}",
        title=new_op.title,
        description=new_op.description,
        date=new_op.date,
        status=new_op.status,
        link=new_op.link,
        created_at=new_op.created_at,
        updated_at=new_op.updated_at,
        user=OpportunityUserSchema.model_validate(user),
    )

# ------------------------------------------------------------------------
# GET /opportunities/{op_id}
# ------------------------------------------------------------------------
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

    # 2) Fetch (or synthesize) user
    user = db.query(Users).get(op.user_id)
    if not user:
        user_data = OpportunityUserSchema(
            id=0,
            email="N/A",
            first_name="N/A",
            last_name="N/A",
            phone_number="N/A",
            student_id=0,
        )
    else:
        user_data = OpportunityUserSchema.model_validate(user)

    # 3) Build full photo URL
    base = str(request.base_url).rstrip("/")
    photo_url = f"{base}{op.photo}"

    return OpportunitySchema(
        **{
            **op.__dict__,
            "photo": photo_url,
            "user": user_data,
        }
    )

@router.delete(
    "/{op_id}/delete",
    status_code=status.HTTP_200_OK,
    summary="Delete a specific opportunity and its associated image",
)
def delete_opportunity(
    op_id: int,
    db: Session = Depends(get_db),
):
    # 1) Fetch
    op = db.query(Opportunities).get(op_id)
    if not op:
        raise HTTPException(status_code=404, detail="Opportunity not found")

    # 2) Delete image file
    path = os.path.join(os.getcwd(), op.photo.lstrip("/"))
    if os.path.isfile(path):
        os.remove(path)

    # 3) Delete record
    db.delete(op)
    db.commit()

    return JSONResponse(
        status_code=200,
        content={"status": "success", "message": f"Opportunity {op_id} deleted successfully."}
    )
