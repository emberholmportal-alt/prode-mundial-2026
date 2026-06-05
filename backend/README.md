# Backend — Prode Mundial 2026

Backend FastAPI + PostgreSQL para el prode interno de Grupo Gestión.
Sirve también el frontend (`frontend/index.html`) desde la misma app.

## Stack

- FastAPI + Uvicorn
- SQLAlchemy 2.0 + Alembic
- PostgreSQL (Render, Ohio)
- JWT (python-jose), bcrypt (passlib)
- Rate limiting con slowapi

## Estructura

```
backend/
├── app/
│   ├── main.py              # FastAPI app, CORS, frontend estático, /health
│   ├── database.py          # engine, SessionLocal, Base, get_db
│   ├── models.py            # User, Prediction, OfficialResult, FinalPick, OfficialFinal
│   ├── schemas.py           # Pydantic v2
│   ├── auth.py              # bcrypt + JWT + dependencias
│   ├── fixtures.py          # FIXTURE (104 partidos) + TEAMS (48 selecciones)
│   ├── deadlines.py         # deadlines por fase (UTC), checks server-side
│   ├── scoring.py           # calc_points, calc_final_points
│   ├── limiter.py           # slowapi Limiter compartido
│   └── routes/
│       ├── auth_routes.py
│       ├── predictions.py
│       ├── final_pick.py
│       ├── leaderboard.py   # cache 30s en memoria
│       ├── admin.py
│       └── fixtures_routes.py
├── alembic/
├── alembic.ini
├── requirements.txt
└── .env.example
```

## Variables de entorno

Copiar `.env.example` a `.env` y completar:

| Variable          | Obligatoria | Descripción                                                                 |
|-------------------|-------------|-----------------------------------------------------------------------------|
| `DATABASE_URL`    | sí          | URL Postgres. Si empieza con `postgres://` se normaliza a `postgresql://`.  |
| `JWT_SECRET`      | sí          | Secret HS256, mínimo 32 caracteres.                                         |
| `ADMIN_USERNAMES` | no          | CSV de usernames lowercase que se vuelven admin al registrarse.             |
| `CORS_ORIGINS`    | no          | CSV de orígenes permitidos. Default `*` (frontend servido desde la misma app). |

## Correr local

```bash
cd backend
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                # editar valores

# Generar y aplicar la migración inicial (la primera vez):
alembic revision --autogenerate -m "initial"
alembic upgrade head

# Levantar la app:
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Frontend en `http://localhost:8000/`, docs en `/docs`, healthcheck en `/health`.

## Deploy en Render

- **Root directory**: `backend`
- **Build command**: `pip install -r requirements.txt`
- **Start command**: `alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- **Health check path**: `/health`
- Conectar el Postgres interno de Render y configurar las env vars (`DATABASE_URL`, `JWT_SECRET`, `ADMIN_USERNAMES`).

## Endpoints

Auth (`/api/auth/*`, rate-limit 5/min en register y login):
- `POST /api/auth/register` — crea usuario. Se vuelve admin si el username está en `ADMIN_USERNAMES`.
- `POST /api/auth/login`
- `GET  /api/auth/me`

Predictions (`/api/predictions/*`, 60/min):
- `GET /api/predictions/me`
- `PUT /api/predictions/{match_id}` — upsert. Valida server-side que la fase no haya cerrado.

Final pick (`/api/final-pick/*`, 60/min):
- `GET /api/final-pick/me`
- `PUT /api/final-pick` — deadline = inicio de semifinales.

Leaderboard (120/min, cache 30s):
- `GET /api/leaderboard`

Admin (`/api/admin/*`, 30/min, requiere `is_admin`):
- `POST   /api/admin/result/{match_id}`
- `DELETE /api/admin/result/{match_id}`
- `POST   /api/admin/final`
- `DELETE /api/admin/final`
- `GET    /api/admin/stats`

Fixtures (público):
- `GET /api/fixtures` — partidos + deadlines UTC por fase
- `GET /api/fixtures/teams` — 48 selecciones con código ISO

Otros:
- `GET /health`
- `GET /` — sirve `frontend/index.html`
- `GET /docs`, `/redoc`

## Notas

- **Sin admin hardcoded**. `is_admin` se setea al registrarse, leyendo `ADMIN_USERNAMES` del entorno.
- **Deadlines validados server-side** en `deadlines.py` — el frontend valida también pero el backend es la fuente de verdad.
- Las migraciones viven en `alembic/versions/` y se generan con `alembic revision --autogenerate` después de cambios en `models.py`.
