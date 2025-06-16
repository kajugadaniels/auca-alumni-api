from fastapi import FastAPI
from database import engine, Base
from routers import students, users

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Student & User API")

app.include_router(
    students.router,
    prefix="/api/students",
    tags=["students"],
)
app.include_router(
    users.router,
    prefix="/api/register",
    tags=["users"],
)
