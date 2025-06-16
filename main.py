from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError, HTTPException as FastAPIHTTPException
from fastapi.responses import JSONResponse
from database import engine, Base
from routers import students, register
Base.metadata.create_all(bind=engine)

app = FastAPI(title="AUCA Alumni")

# Custom exception handler for request validation errors
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    return JSONResponse(
        status_code=422,
        content={
            "status": "error",
            "message": "Validation error",
            "errors": errors,
        },
    )

# Custom handler for HTTPExceptions
@app.exception_handler(FastAPIHTTPException)
async def http_exception_handler(request: Request, exc: FastAPIHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status": "error",
            "message": exc.detail,
        },
    )

# Include routers
app.include_router(
    students.router,
    prefix="/api/students",
    tags=["students"],
)

app.include_router(
    register.router,
    prefix="/api/auth",
    tags=["auth"],
)
