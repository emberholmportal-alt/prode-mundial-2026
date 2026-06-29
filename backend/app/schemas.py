from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class UserOut(BaseModel):
    """Vista pública del usuario (sin campos privados)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    display_name: str
    is_admin: bool
    company: str
    city: str
    avatar_config: Optional[str] = None
    created_at: datetime


class UserPrivateOut(UserOut):
    """Vista con campos privados — sólo si quien consulta es el dueño o un admin."""

    dni: str
    email: str
    sector: str
    must_change_password: bool = False


class ChangePasswordIn(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


class RegisterIn(BaseModel):
    username: str = Field(min_length=3, max_length=30)
    password: str = Field(min_length=8, max_length=128)
    display_name: str = Field(min_length=3, max_length=100)
    dni: str = Field(min_length=7, max_length=10, pattern=r"^\d+$")
    email: EmailStr
    sector: str = Field(min_length=2, max_length=100)
    company: Literal["grupo_gestion", "carrefour"]
    city: Literal["isidro_casanova", "esteban_echeverria"]


class LoginIn(BaseModel):
    username: str
    password: str


class AuthOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserPrivateOut


class PredictionIn(BaseModel):
    # home_score / away_score corresponden a 90' + alargue (sin penales).
    home_score: int = Field(ge=0, le=20)
    away_score: int = Field(ge=0, le=20)
    # Solo para knockouts con empate después de 90'+ET. Es el TLA del
    # equipo que el usuario cree que pasa por penales.
    penalty_winner: Optional[str] = Field(default=None, min_length=3, max_length=3)


class PredictionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    match_id: str
    home_score: int
    away_score: int
    penalty_winner: Optional[str] = None
    updated_at: datetime


class FinalPickIn(BaseModel):
    champion: str = Field(min_length=3, max_length=3)
    runner_up: str = Field(min_length=3, max_length=3)


class FinalPickOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    champion: str
    runner_up: str
    updated_at: datetime


class OfficialResultIn(BaseModel):
    # Marcador después de 90' + alargue (sin contar penales).
    home_score: int = Field(ge=0, le=20)
    away_score: int = Field(ge=0, le=20)
    # TLA del equipo que ganó por penales (solo aplica si quedó empatado).
    penalty_winner: Optional[str] = Field(default=None, min_length=3, max_length=3)


class OfficialResultOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    match_id: str
    home_score: int
    away_score: int
    penalty_winner: Optional[str] = None
    auto_loaded: bool = False
    updated_at: datetime


class OfficialFinalIn(BaseModel):
    champion: str = Field(min_length=3, max_length=3)
    runner_up: str = Field(min_length=3, max_length=3)


class OfficialFinalOut(BaseModel):
    champion: Optional[str]
    runner_up: Optional[str]
    updated_at: Optional[datetime]


class LeaderboardRow(BaseModel):
    username: str
    display_name: str
    company: str
    city: str
    avatar_config: Optional[str] = None
    points: int
    predicted_count: int
    correct_exact: int
    correct_result: int
    # Promedio (en segundos) de anticipación con la que cargó/editó cada
    # pronóstico respecto al kickoff. Se usa como criterio de desempate
    # cuando puntos + aciertos están iguales. None si no tiene pronósticos.
    avg_anticipation_seconds: Optional[float] = None


_AVATAR_STYLES = {"avataaars"}


class AvatarConfigIn(BaseModel):
    style: str = Field(default="avataaars", max_length=30)
    skin_color: Optional[str] = Field(default=None, max_length=20)
    top: Optional[str] = Field(default=None, max_length=40)
    hair_color: Optional[str] = Field(default=None, max_length=20)
    facial_hair: Optional[str] = Field(default=None, max_length=40)
    clothing: Optional[str] = Field(default=None, max_length=40)
    accessories: Optional[str] = Field(default=None, max_length=40)
    background_color: Optional[str] = Field(default=None, max_length=20)
    seed: Optional[str] = Field(default=None, max_length=60)

    @field_validator("style")
    @classmethod
    def _validate_style(cls, v: str) -> str:
        if v not in _AVATAR_STYLES:
            raise ValueError(f"Estilo de avatar no soportado: {v}")
        return v


class AvatarConfigOut(BaseModel):
    avatar_config: Optional[str] = None


class UserUpdateAdminIn(BaseModel):
    """Campos que un admin puede modificar de un usuario existente. Por ahora
    solo display_name (para corregir nombres incompletos cargados al registrarse)."""

    display_name: str = Field(min_length=3, max_length=100)


class CommentIn(BaseModel):
    body: str = Field(min_length=1, max_length=500)
    parent_id: Optional[int] = None  # None = comentario raíz; int = respuesta


class CommentOut(BaseModel):
    id: int
    user_id: int
    username: str
    display_name: str
    sector: str
    company: str
    city: str
    body: str
    parent_id: Optional[int] = None
    likes_count: int = 0
    liked_by_me: bool = False
    created_at: datetime
    updated_at: Optional[datetime] = None


class CommentLikerOut(BaseModel):
    username: str
    display_name: str
    company: str
    city: str
    created_at: datetime


class AdminStats(BaseModel):
    users_count: int
    predictions_count: int
    official_results_count: int
    final_picks_count: int
    official_final_set: bool


class FixtureMatch(BaseModel):
    id: str
    phase: str
    group: Optional[str]
    home: str
    away: str
    datetime_art: str
    datetime_utc: str
    venue: str


class TeamOut(BaseModel):
    code: str
    name: str
    iso: str
