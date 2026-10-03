from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.api import (
    auth,
    elevations,
    files,
    materials,
    plans,
    projects,
    recommendations,
    terrains,
    undo,
)
from app.errors import (
    AuthenticationError,
    ConflictError,
    FileTooLargeError,
    NotFoundError,
    UnsupportedFileError,
)

app = FastAPI(title="ARQUILA API", version="1.0.0")

app.include_router(auth.router)
app.include_router(files.router)
app.include_router(projects.router)
app.include_router(terrains.router)
app.include_router(materials.router)
app.include_router(plans.router)
app.include_router(elevations.router)
app.include_router(recommendations.router)
app.include_router(undo.router)


@app.exception_handler(AuthenticationError)
def handle_unauthenticated(request: Request, error: AuthenticationError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED, content={"detail": str(error)}
    )


@app.exception_handler(NotFoundError)
def handle_not_found(request: Request, error: NotFoundError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND, content={"detail": str(error)}
    )


@app.exception_handler(ConflictError)
def handle_conflict(request: Request, error: ConflictError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT, content={"detail": str(error)}
    )


@app.exception_handler(UnsupportedFileError)
def handle_unsupported_file(request: Request, error: UnsupportedFileError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
        content={"detail": str(error)},
    )


@app.exception_handler(FileTooLargeError)
def handle_file_too_large(request: Request, error: FileTooLargeError) -> JSONResponse:
    return JSONResponse(status_code=413, content={"detail": str(error)})


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
