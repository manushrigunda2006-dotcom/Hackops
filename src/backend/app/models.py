"""ORM models. Mirrors ../../DATA-MODEL.md — keep that file in sync if
you change anything here.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def _uuid() -> str:
    return uuid.uuid4().hex


def _now() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    """Global identity. Role is NOT stored here — see Role."""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    email: Mapped[str] = mapped_column(String, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String)
    name: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    roles: Mapped[list["Role"]] = relationship(back_populates="user")


class Role(Base):
    """user x event x role. Roles are scoped per-event, not global —
    see ARCHITECTURE.md 'Why per-event roles'.
    """

    __tablename__ = "roles"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    event_id: Mapped[str] = mapped_column(ForeignKey("events.id"))
    role: Mapped[str] = mapped_column(String)  # participant|judge|organizer|admin

    user: Mapped["User"] = relationship(back_populates="roles")


class Event(Base):
    __tablename__ = "events"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String)
    description: Mapped[str] = mapped_column(String, default="")
    submissions_open_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    submissions_close_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Track(Base):
    __tablename__ = "tracks"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    event_id: Mapped[str] = mapped_column(ForeignKey("events.id"))
    name: Mapped[str] = mapped_column(String)


class Prize(Base):
    __tablename__ = "prizes"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    event_id: Mapped[str] = mapped_column(ForeignKey("events.id"))
    name: Mapped[str] = mapped_column(String)
    description: Mapped[str] = mapped_column(String, default="")
    rank_or_category: Mapped[str] = mapped_column(String, default="")


class Team(Base):
    __tablename__ = "teams"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    event_id: Mapped[str] = mapped_column(ForeignKey("events.id"))
    name: Mapped[str] = mapped_column(String)
    invite_token: Mapped[str] = mapped_column(String, unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class TeamMember(Base):
    __tablename__ = "team_members"

    team_id: Mapped[str] = mapped_column(ForeignKey("teams.id"), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), primary_key=True)
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    team_id: Mapped[str] = mapped_column(ForeignKey("teams.id"))
    track_id: Mapped[str] = mapped_column(ForeignKey("tracks.id"), nullable=True)
    title: Mapped[str] = mapped_column(String)
    summary: Mapped[str] = mapped_column(String, default="")
    repo_url: Mapped[str] = mapped_column(String, default="")
    status: Mapped[str] = mapped_column(String, default="draft")  # draft|submitted
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)


class ProjectRevision(Base):
    """Cheap insurance for later audit-trail needs (T3)."""

    __tablename__ = "project_revisions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"))
    snapshot_json: Mapped[str] = mapped_column(String)
    edited_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Session(Base):
    """Auth sessions. Both the real login flow and the acceptance
    checker's pre-issued header tokens (.dogfood.toml [auth]) resolve
    through this same table — see app/auth.py.
    """

    __tablename__ = "sessions"

    token: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


# ==================== T2 JUDGING MODELS ====================

class JudgeAssignment(Base):
    """Assigns a judge to a project for a specific event."""

    __tablename__ = "judge_assignments"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    judge_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"))
    event_id: Mapped[str] = mapped_column(ForeignKey("events.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class RubricCriterion(Base):
    """Configurable judging criterion and its weight."""

    __tablename__ = "rubric_criteria"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    event_id: Mapped[str] = mapped_column(ForeignKey("events.id"))
    name: Mapped[str] = mapped_column(String)
    weight: Mapped[float] = mapped_column(default=1.0)
    max_score: Mapped[float] = mapped_column(default=5.0)


class JudgeScore(Base):
    """A score submitted by one judge for one project."""

    __tablename__ = "judge_scores"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    judge_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"))
    event_id: Mapped[str] = mapped_column(ForeignKey("events.id"))
    criteria_json: Mapped[str] = mapped_column(String)
    comment: Mapped[str] = mapped_column(String, default="")
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
