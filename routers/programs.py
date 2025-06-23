import os
import datetime
from typing import Optional
from PIL import Image

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
    UploadFile,
    File,
    Form,
    Request,
    Query,
)
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from database import get_db
from models import Programs
from schemas.program import (
    CreateProgramSchema,
    ProgramSchema,
    ProgramListResponse,
)
from routers.auth import get_current_user

router = APIRouter(
    # prefix="/programs",
    tags=["programs"],
    dependencies=[Depends(get_current_user)],
)

# Directory for program uploads
PROGRAMS_UPLOAD_DIR = os.path.join(os.getcwd(), "uploads", "programs")
os.makedirs(PROGRAMS_UPLOAD_DIR, exist_ok=True)

# ------------------------------------------------------------------------
# GET /programs: list all programs with pagination, search, sorting
# ------------------------------------------------------------------------
@router.get(
    "/programs",
    response_model=ProgramListResponse,
    summary="Retrieve a paginated list of programs with metadata and image URLs",
)
def list_programs(
    request: Request,
    *,
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Filter by title or description"),
    sort_by: str = Query(
        "created_at",
        regex="^(id|title|created_at)$",
        description="Field to sort by; defaults to `created_at`",
    ),
    order: str = Query(
        "desc",
        regex="^(asc|desc)$",
        description="Sort direction; defaults to descending (latest first)",
    ),
) -> ProgramListResponse:
    """
    Retrieve all programs with:
    - total count of records
    - pagination metadata
    - full URLs for the `photo` field
    """
    # 1) Total count
    total = db.query(func.count(Programs.id)).scalar()

    # 2) Base query
    query = db.query(Programs)
    if search:
        term = f"%{search.strip()}%"
        query = query.filter(
            Programs.title.ilike(term) | Programs.description.ilike(term)
        )

    # 3) Ordering
    direction = asc if order == "asc" else desc
    column = getattr(Programs, sort_by)
    query = query.order_by(direction(column))

    # 4) Pagination
    offset = (page - 1) * page_size
    raw_items = query.offset(offset).limit(page_size).all()
    if not raw_items and page != 1:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Page out of range")

    # 5) Build items with full photo URLs
    base = str(request.base_url).rstrip("/")
    items = []
    for prog in raw_items:
        photo_url = f"{base}{prog.photo}"
        items.append(
            ProgramSchema(
                id=prog.id,
                title=prog.title,
                description=prog.description,
                photo=photo_url,
                created_at=prog.created_at,
                updated_at=prog.updated_at,
            )
        )

    # 6) Navigation URLs
    def make_url(p: int) -> str:
        return str(request.url.include_query_params(page=p, page_size=page_size))

    prev_page = make_url(page - 1) if page > 1 else None
    next_page = make_url(page + 1) if offset + len(items) < total else None

    return ProgramListResponse(
        total=total,
        page=page,
        page_size=page_size,
        next_page=next_page,
        prev_page=prev_page,
        items=items,
    )

# ------------------------------------------------------------------------
# POST /programs/add: create a new program with image upload and processing
# ------------------------------------------------------------------------
@router.post(
    "/program/add/",
    status_code=status.HTTP_201_CREATED,
    summary="Create a new program with image upload and auto-crop",
)
async def add_program(
    request: Request,
    title: str = Form(..., min_length=5, description="Program title"),
    description: str = Form(..., min_length=10, description="Program description"),
    photo: UploadFile = File(..., description="Image file for the program"),
    db: Session = Depends(get_db),
):
    """
    Creates a new program:
    - Validates title and description
    - Saves and crops image (1270×720)
    - Persists record and returns full metadata
    """
    # 1) Validate metadata
    data = CreateProgramSchema(title=title, description=description)

    # 2) Prevent duplicate
    if db.query(Programs).filter(Programs.title == data.title.strip()).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "program_exists",
                "message": f"A program titled '{data.title}' already exists."
            },
        )

    # 3) Build filename
    slug = "".join(
        c for c in data.title.lower().replace(" ", "_") if c.isalnum() or c == "_"
    )
    date_str = datetime.date.today().strftime("%Y%m%d")
    ext = os.path.splitext(photo.filename)[1] or ".jpg"
    filename = f"{slug}_{date_str}{ext}"
    filepath = os.path.join(PROGRAMS_UPLOAD_DIR, filename)

    # 4) Save and crop image
    contents = await photo.read()
    with open(filepath, "wb") as f:
        f.write(contents)

    try:
        img = Image.open(filepath)
        img = img.convert("RGB")
        img = img.resize((1270, 720), Image.LANCZOS)
        img.save(filepath, quality=85)
    except Exception:
        os.remove(filepath)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "invalid_image",
                "message": "Uploaded file is not a valid image."
            },
        )

    # 5) Persist record
    new_prog = Programs(
        title=data.title.strip(),
        description=data.description.strip(),
        photo=f"/uploads/programs/{filename}",
    )
    db.add(new_prog)
    db.commit()
    db.refresh(new_prog)

    # 6) Build full photo URL
    base = str(request.base_url).rstrip("/")
    photo_url = f"{base}{new_prog.photo}"

    # 7) Return success JSON
    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={
            "status": "success",
            "message": "Program created successfully.",
            "program": {
                "id": new_prog.id,
                "title": new_prog.title,
                "description": new_prog.description,
                "photo": photo_url,
                "created_at": new_prog.created_at.isoformat(),
                "updated_at": new_prog.updated_at.isoformat(),
            },
        },
    )

# ------------------------------------------------------------------------
# GET /programs/{program_id}: retrieve detailed information for a single program
# ------------------------------------------------------------------------
@router.get(
    "/program/{program_id}",
    response_model=ProgramSchema,
    summary="Retrieve detailed information for a single program by ID",
)
def get_program_details(
    program_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Fetch a single program record by its ID.
    Returns 404 if not found, otherwise full metadata with image URL.
    """
    program = db.query(Programs).get(program_id)
    if not program:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "program_not_found",
                "message": f"No program found with ID {program_id}."
            },
        )

    # Build full photo URL
    base = str(request.base_url).rstrip("/")
    photo_url = f"{base}{program.photo}"

    return ProgramSchema(
        id=program.id,
        title=program.title,
        description=program.description,
        photo=photo_url,
        created_at=program.created_at,
        updated_at=program.updated_at,
    )

# ------------------------------------------------------------------------
# PUT /programs/{program_id}: update an existing program
# ------------------------------------------------------------------------
@router.put(
    "/{program_id}",
    response_model=ProgramSchema,
    summary="Update an existing program by ID",
)
async def update_program(
    program_id: int,
    request: Request,
    title: str = Form(..., min_length=5, description="Updated program title"),
    description: str = Form(..., min_length=10, description="Updated program description"),
    photo: Optional[UploadFile] = File(None, description="New image file (optional)"),
    db: Session = Depends(get_db),
):
    """
    Update fields of a program:
    - Validates title/description via CreateProgramSchema
    - Prevents duplicate titles on other records
    - Optionally replaces, renames, and crops the image to 1270×720
    """
    # 1) Fetch existing record
    prog = db.query(Programs).get(program_id)
    if not prog:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "program_not_found",
                "message": f"No program found with ID {program_id}."
            },
        )

    # 2) Validate metadata
    data = CreateProgramSchema(title=title, description=description)

    # 3) Prevent duplicate titles
    dup = db.query(Programs).filter(
        Programs.id != program_id,
        Programs.title == data.title.strip()
    ).first()
    if dup:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "program_exists",
                "message": f"Another program titled '{data.title}' already exists."
            },
        )

    # 4) Apply updates
    prog.title = data.title.strip()
    prog.description = data.description.strip()

    # 5) Handle new photo if provided
    if photo:
        # Remove old file
        old_path = os.path.join(os.getcwd(), prog.photo.lstrip("/"))
        if os.path.isfile(old_path):
            try:
                os.remove(old_path)
            except Exception:
                pass  # log in production

        # Build new filename
        slug = "".join(c for c in data.title.lower().replace(" ", "_") if c.isalnum() or c == "_")
        date_str = datetime.date.today().strftime("%Y%m%d")
        ext = os.path.splitext(photo.filename)[1] or ".jpg"
        filename = f"{slug}_{date_str}{ext}"
        filepath = os.path.join(PROGRAMS_UPLOAD_DIR, filename)

        # Save and crop
        contents = await photo.read()
        with open(filepath, "wb") as f:
            f.write(contents)

        try:
            img = Image.open(filepath)
            img = img.convert("RGB")
            img = img.resize((1270, 720), Image.LANCZOS)
            img.save(filepath, quality=85)
        except Exception:
            os.remove(filepath)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "invalid_image",
                    "message": "Uploaded file is not a valid image."
                },
            )

        prog.photo = f"/uploads/programs/{filename}"

    # 6) Commit changes
    db.add(prog)
    db.commit()
    db.refresh(prog)

    # 7) Build full photo URL
    base = str(request.base_url).rstrip("/")
    photo_url = f"{base}{prog.photo}"

    # 8) Return updated record
    return ProgramSchema(
        id=prog.id,
        title=prog.title,
        description=prog.description,
        photo=photo_url,
        created_at=prog.created_at,
        updated_at=prog.updated_at,
    )