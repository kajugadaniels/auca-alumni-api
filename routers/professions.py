from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
    Request,
    Query,
    Body,
)
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import asc, desc, func
from typing import Optional
from fastapi.encoders import jsonable_encoder

from database import get_db
from models import Professions
from schemas.professions import (
    CreateProfessionSchema,
    ProfessionSchema,
    ProfessionListResponse,
)
from routers.auth import get_current_user

router = APIRouter(
    prefix="/professions",
    tags=["professions"],
    dependencies=[Depends(get_current_user)],
)

@router.get(
    "/",
    response_model=ProfessionListResponse,
    summary="Retrieve a paginated list of professions",
)
def list_professions(
    request: Request,
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Filter by name"),
    sort_by: str = Query(
        "created_at",
        regex="^(id|name|created_at)$",
        description="Field to sort by",
    ),
    order: str = Query(
        "desc",
        regex="^(asc|desc)$",
        description="Sort direction",
    ),
) -> ProfessionListResponse:
    """
    List professions with pagination and optional name search.
    """
    total = db.query(func.count(Professions.id)).scalar()
    query = db.query(Professions)
    if search:
        term = f"%{search.strip()}%"
        query = query.filter(Professions.name.ilike(term))

    direction = asc if order == "asc" else desc
    column = getattr(Professions, sort_by)
    query = query.order_by(direction(column))

    offset = (page - 1) * page_size
    raw_items = query.offset(offset).limit(page_size).all()
    if not raw_items and page != 1:
        raise HTTPException(status_code=404, detail="Page out of range")

    # Use model_validate() instead of from_attributes()
    items = [ProfessionSchema.model_validate(prof) for prof in raw_items]

    def make_url(p: int) -> str:
        return str(request.url.include_query_params(page=p, page_size=page_size))

    prev_page = make_url(page - 1) if page > 1 else None
    next_page = make_url(page + 1) if offset + len(items) < total else None

    return ProfessionListResponse(
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
    summary="Create a new profession",
)
def add_profession(
    name: str = Form(..., description="Profession name"),
    db: Session = Depends(get_db),
):
    """
    Create a new profession. Prevents duplicates by name.
    """
    # 1) Validate input via Pydantic
    data = CreateProfessionSchema(name=name)
    clean_name = data.name

    # 2) Duplicate check
    if db.query(Professions).filter_by(name=clean_name).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "profession_exists",
                "message": f"Profession '{clean_name}' already exists."
            },
        )

    # 3) Persist
    new_prof = Professions(name=clean_name)
    db.add(new_prof)
    db.commit()
    db.refresh(new_prof)

    # 4) Build response
    envelope = {
        "status": "success",
        "message": "Profession created successfully.",
        "profession": ProfessionSchema.model_validate(new_prof)
    }

    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content=jsonable_encoder(envelope),
    )

@router.get(
    "/{profession_id}",
    response_model=ProfessionSchema,
    summary="Retrieve a single profession by ID",
)
def get_profession(
    profession_id: int,
    db: Session = Depends(get_db),
):
    prof = db.query(Professions).get(profession_id)
    if not prof:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "not_found", "message": f"No profession found with ID {profession_id}."},
        )
    return ProfessionSchema.model_validate(prof)

@router.put(
    "/{profession_id}/update",
    response_model=ProfessionSchema,
    summary="Update an existing profession by ID",
)
def update_profession(
    profession_id: int,
    data: CreateProfessionSchema = Body(...),
    db: Session = Depends(get_db),
):
    """
    Update the name of a profession, preventing duplicates.
    """
    prof = db.query(Professions).get(profession_id)
    if not prof:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "not_found", "message": f"No profession found with ID {profession_id}."},
        )

    new_name = data.name.strip()
    if (
        db.query(Professions)
        .filter(Professions.id != profession_id, Professions.name == new_name)
        .first()
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "profession_exists", "message": f"Another profession named '{new_name}' exists."},
        )

    prof.name = new_name
    db.commit()
    db.refresh(prof)
    return ProfessionSchema.from_attributes(prof)

@router.delete(
    "/{profession_id}/delete",
    status_code=status.HTTP_200_OK,
    summary="Delete a profession by ID",
)
def delete_profession(
    profession_id: int,
    db: Session = Depends(get_db),
):
    """
    Deletes the profession record identified by `profession_id`.
    """
    prof = db.query(Professions).get(profession_id)
    if not prof:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "not_found", "message": f"No profession found with ID {profession_id}."},
        )

    db.delete(prof)
    db.commit()
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"status": "success", "message": f"Profession ID {profession_id} deleted successfully."},
    )
