from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    display_name: str
    is_admin: bool
    created_at: datetime


class RegisterIn(BaseModel):
    username: str = Field(min_length=3, max_length=30)
    password: str = Field(min_length=8, max_length=128)
    display_name: str = Field(min_length=1, max_length=100)


class LoginIn(BaseModel):
    username: str
    password: str


class AuthOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class PredictionIn(BaseModel):
    home_score: int = Field(ge=0, le=20)
    away_score: int = Field(ge=0, le=20)


class PredictionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    match_id: str
    home_score: int
    away_score: int
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
    home_score: int = Field(ge=0, le=20)
    away_score: int = Field(ge=0, le=20)


class OfficialResultOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    match_id: str
    home_score: int
    away_score: int
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
    points: int
    predicted_count: int
    correct_exact: int
    correct_result: int


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
