from fastapi import FastAPI
from database import engine, Base
from routers import students

# Create DB tables (if you prefer auto-create; otherwise handle migrations separately)
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Student API")

# Include routers
app.include_router(
    students.router,
    prefix="/api/students",
    tags=["students"],
)
