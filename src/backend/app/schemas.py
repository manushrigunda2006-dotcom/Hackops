from datetime import datetime

from pydantic import BaseModel, Field


class LoginIn(BaseModel):
    email: str
    password: str


class MeOut(BaseModel):
    id: str
    email: str
    name: str
    roles: list[dict]


class EventOut(BaseModel):
    id: str
    name: str
    description: str
    submissions_open_at: str
    submissions_close_at: str


class EventCreateIn(BaseModel):
    name: str
    submissions_open_at: datetime
    submissions_close_at: datetime
    tracks: list[str] = Field(default_factory=list)


class TeamJoinIn(BaseModel):
    invite_token: str


class TeamOut(BaseModel):
    id: str
    name: str
    event_id: str


class ProjectCreateIn(BaseModel):
    title: str
    summary: str = ""
    repo_url: str = ""


class ProjectOut(BaseModel):
    id: str
    team_id: str
    team_name: str
    track_id: str | None
    track_name: str | None
    title: str
    summary: str
    repo_url: str
    status: str
    submitted_at: str | None
    updated_at: str | None
