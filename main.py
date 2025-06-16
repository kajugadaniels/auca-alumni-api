"""
Main application entry point: include routers and exception handlers.
"""
from database import engine, Base
from routers import students, auth
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError, HTTPException as FastAPIHTTPException

# Auto-create tables (or manage migrations externally)
Base.metadata.create_all(bind=engine)
app = FastAPI(title="AUCA Alumni with Unified Auth")

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

# Include student router under /api
app.include_router(
    students.router,
    prefix="/api",
    tags=["students"],
)

# Include unified auth router under /api/auth
app.include_router(
    auth.router,
    prefix="/api/auth",
    tags=["auth"],
)