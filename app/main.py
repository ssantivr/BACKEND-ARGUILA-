from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.api import (
    elevations,
    materials,
    plans,
    projects,
    recommendations,
    terrains,
    undo,
    users,
)
from app.errors import ConflictError, NotFoundError

app = FastAPI(title="ARQUILA API", version="1.0.0")

app.include_router(users.router)
app.include_router(projects.router)
app.include_router(terrains.router)
app.include_router(materials.router)
app.include_router(plans.router)
app.include_router(elevations.router)
app.include_router(recommendations.router)
app.include_router(undo.router)


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


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
