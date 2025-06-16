from typing import List, Optional
from fastapi import FastAPI, Depends, HTTPException, Query
from sqlalchemy import asc, desc
from sqlalchemy.orm import Session
from pydantic import BaseModel

import database
import models

app = FastAPI()


# 1. Dependency: create & teardown DB session
def get_db():
    """
    Provide a transactional SQLAlchemy session, and close it after use.
    """
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

# git commit -m "Add database session dependency"


# 2. Pydantic schema for Student
class StudentSchema(BaseModel):
    id: int
    id_number: int
    first_name: str
    last_name: str

    class Config:
        orm_mode = True  # tell Pydantic to read data via attribute access


# 3. GET /students endpoint with pagination, search, and ordering
@app.get("/api/students", response_model=List[StudentSchema])
def get_students(
    *,
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(10, ge=1, le=100, description="Number of items per page"),
    search: Optional[str] = Query(None, description="Filter by first or last name"),
    sort_by: str = Query("created_at", regex="^(id|id_number|first_name|last_name|created_at)$",
                         description="Field to sort by"),
    order: str = Query("desc", regex="^(asc|desc)$", description="Sort direction"),
) -> List[StudentSchema]:
    """
    Retrieve a paginated list of students, optionally filtered and ordered.
    """
    # Base query
    query = db.query(models.Students)

    # 1) Search filter
    if search:
        term = f"%{search.strip()}%"
        query = query.filter(
            models.Students.first_name.ilike(term) |
            models.Students.last_name.ilike(term)
        )

    # 2) Ordering
    direction = asc if order == "asc" else desc
    column = getattr(models.Students, sort_by)
    query = query.order_by(direction(column))

    # 3) Pagination
    offset = (page - 1) * page_size
    students = query.offset(offset).limit(page_size).all()

    if not students and page != 1:
        raise HTTPException(status_code=404, detail="Page out of range")

    return students

# git commit -m "Add get_students endpoint with pagination, search, and ordering"
