from database import engine, Base
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError, HTTPException as FastAPIHTTPException
from routers import students, auth, countries, events, news, programs, social_activities, sliders, professions, faculties, work_experiences, personal_information, opportunity_histories

# Auto-create tables (or manage migrations externally)
Base.metadata.create_all(bind=engine)

app = FastAPI(title="AUCA Alumni")

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
    opportunity_histories.router,
    prefix="/api",
    tags=["opportunity_histories"],
)