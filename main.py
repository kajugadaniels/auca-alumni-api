from database import engine, Base
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError, HTTPException as FastAPIHTTPException
from routers import (
    students,
    auth,
    countries,
    events,
    news,
    programs,
    social_activities,
    sliders,
    professions,
    faculties,
    work_experiences,
    personal_information,
    opportunities,
    opportunity_histories,
    executive_committees,
    departments,
    certifications,
    discussions,
)

# Auto-create tables (or manage migrations externally)
Base.metadata.create_all(bind=engine)

app = FastAPI(title="AUCA Alumni")

# CORS configuration
origins = [
    "http://localhost:5173",  # The frontend running on this URL
    "http://127.0.0.1:5173",  # You can also add more URLs if needed
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # Allows requests from these origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods (GET, POST, etc.)
    allow_headers=["*"],  # Allows all headers
)

# Serve uploaded images
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# Exception handler for Pydantic validation errors
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "status": "error",
            "message": "Validation error",
            "errors": exc.errors(),
        },
    )

# Exception handler for HTTPException
@app.exception_handler(FastAPIHTTPException)
async def http_exception_handler(request: Request, exc: FastAPIHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"status": "error", "message": exc.detail},
    )

app.include_router(
    students.router,
    prefix="/api",
    tags=["students"],
)

app.include_router(
    auth.router,
    prefix="/api/auth",
    tags=["auth"],
)

app.include_router(
    countries.router,
    prefix="/api",
    tags=["countries"],
)

app.include_router(
    events.router,
    prefix="/api",
    tags=["events"],
)

app.include_router(
    news.router,
    prefix="/api",
    tags=["news"],
)

app.include_router(
    programs.router,
    prefix="/api",
    tags=["programs"],
)

app.include_router(
    social_activities.router,
    prefix="/api",
    tags=["social-activities"],
)

app.include_router(
    sliders.router,
    prefix="/api",
    tags=["sliders"],
)

app.include_router(
    professions.router,
    prefix="/api",
    tags=["professions"],
)

app.include_router(
    faculties.router,
    prefix="/api",
    tags=["faculties"],
)

app.include_router(
    work_experiences.router,
    prefix="/api",
    tags=["work_experiences"],
)

app.include_router(
    personal_information.router,
    prefix="/api",
    tags=["personal_information"],
)

app.include_router(
    opportunities.router,
    prefix="/api",
    tags=["opportunities"],
)

app.include_router(
    opportunity_histories.router,
    prefix="/api",
    tags=["opportunity_histories"],
)

app.include_router(
    executive_committees.router,
    prefix="/api",
    tags=["executive_committees"],
)

app.include_router(
    departments.router,
    prefix="/api",
    tags=["departments"],
)

app.include_router(
    certifications.router,
    prefix="/api",
    tags=["certifications"],
)

app.include_router(
    discussions.router,
    prefix="/api",
    tags=["discussions"],
)

app.include_router(
    donations.router,
    prefix="/api",
    tags=["donations"],
)