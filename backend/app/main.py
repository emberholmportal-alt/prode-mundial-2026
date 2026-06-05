import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from .limiter import limiter
from .routes import (
    admin,
    auth_routes,
    final_pick,
    fixtures_routes,
    leaderboard,
    predictions,
)

load_dotenv()


FRONTEND_DIR = Path(__file__).resolve().parent.parent.parent / "frontend"
INDEX_HTML = FRONTEND_DIR / "index.html"
ASSETS_DIR = FRONTEND_DIR / "assets"

CORS_ORIGINS = [
    o.strip() for o in os.environ.get("CORS_ORIGINS", "*").split(",") if o.strip()
]


app = FastAPI(title="Prode Mundial 2026", version="1.0.0")

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials="*" not in CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=getattr(exc, "headers", None),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={"detail": "Datos inválidos", "errors": exc.errors()},
    )


app.include_router(auth_routes.router, prefix="/api")
app.include_router(predictions.router, prefix="/api")
app.include_router(final_pick.router, prefix="/api")
app.include_router(leaderboard.router, prefix="/api")
app.include_router(admin.router, prefix="/api")
app.include_router(fixtures_routes.router, prefix="/api")


@app.get("/health")
def health():
    return {"status": "ok"}


if ASSETS_DIR.is_dir():
    app.mount("/assets", StaticFiles(directory=str(ASSETS_DIR)), name="assets")


@app.get("/", include_in_schema=False)
def serve_frontend():
    if INDEX_HTML.is_file():
        return FileResponse(str(INDEX_HTML))
    return JSONResponse(status_code=404, content={"detail": "Frontend no encontrado"})
