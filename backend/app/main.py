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

from sqlalchemy import update

from .auth import ADMIN_USERNAMES
from .database import SessionLocal
from .limiter import limiter
from .models import User
from .routes import (
    admin,
    audit_routes,
    auth_routes,
    comments_routes,
    final_pick,
    fixtures_routes,
    leaderboard,
    live_routes,
    me_routes,
    predictions,
    results_routes,
)

load_dotenv()


FRONTEND_DIR = Path(__file__).resolve().parent.parent.parent / "frontend"
INDEX_HTML = FRONTEND_DIR / "index.html"
ASSETS_DIR = FRONTEND_DIR / "assets"

CORS_ORIGINS = [
    o.strip() for o in os.environ.get("CORS_ORIGINS", "*").split(",") if o.strip()
]


app = FastAPI(title="Prode Mundial 2026", version="1.0.0")


@app.on_event("startup")
def _promote_admins_on_startup() -> None:
    """Si un usuario ya registrado coincide con ADMIN_USERNAMES, asegurarnos
    de que tenga is_admin=true. Útil cuando se agrega un username admin
    nuevo en el env sin reset de la DB."""
    if not ADMIN_USERNAMES:
        return
    db = SessionLocal()
    try:
        db.execute(
            update(User)
            .where(User.username.in_(ADMIN_USERNAMES))
            .where(User.is_admin.is_(False))
            .values(is_admin=True)
        )
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()


@app.on_event("startup")
def _apply_knockout_overrides_on_startup() -> None:
    """En boot, aplica las asignaciones de knockout_matches sobre FIXTURE_BY_ID
    en memoria. Sin esto, después de un restart los slots K vuelven a sus
    valores tentativos hasta que pase la primera pasada del sync — y mientras
    tanto los deadlines se calculan con kickoff erróneo."""
    from .fixtures import apply_knockout_overrides
    db = SessionLocal()
    try:
        apply_knockout_overrides(db)
    finally:
        db.close()


@app.on_event("startup")
def _start_background_sync_on_startup() -> None:
    """Arranca el scheduler que sincroniza resultados/cruces periódicamente,
    sin depender de que haya usuarios con la app abierta."""
    from .routes.live_routes import start_background_sync
    start_background_sync()


@app.on_event("shutdown")
def _stop_background_sync_on_shutdown() -> None:
    from .routes.live_routes import stop_background_sync
    stop_background_sync()

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
app.include_router(results_routes.router, prefix="/api")
app.include_router(comments_routes.router, prefix="/api")
app.include_router(live_routes.router, prefix="/api")
app.include_router(me_routes.router, prefix="/api")
app.include_router(audit_routes.router, prefix="/api")


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
