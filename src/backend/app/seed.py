"""Loads data/fixtures.json into SQLite on first boot.

Idempotent: if an Event row already exists, seeding is skipped, so
restarting the container doesn't wipe anything a demo has added.

Also creates the four checker-facing accounts from .dogfood.toml
[auth], with fixed session tokens, so `docker compose up` alone is
enough for `python3 run.py .dogfood.toml` to work — no login step,
per the "checker never logs in" rule in the spec.

Every seeded human account (organizer, judges, participants) also gets
the same demo password, "dogfood", so a person can log in through the
real UI for the demo video using any fixture email.
"""

import json
import os
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session as DBSession

from . import models
from .auth import hash_password
from .database import Base, SessionLocal, engine
from .util import to_naive_utc

FIXTURES_PATH = os.environ.get("DOGFOOD_FIXTURES_PATH", "/app/data/fixtures.json")
DEMO_PASSWORD = "dogfood"

# Fixed tokens — must match .dogfood.toml [auth] exactly.
TOKEN_ORGANIZER = "org_7f2a"
TOKEN_JUDGE_A = "jdg_a_91bc"
TOKEN_JUDGE_B = "jdg_b_44de"
TOKEN_PARTICIPANT = "prt_2e88"


def _parse_dt(s: str) -> datetime:
    return to_naive_utc(datetime.fromisoformat(s.replace("Z", "+00:00")))


def _get_or_create_user(db: DBSession, email: str, name: str) -> models.User:
    user = db.query(models.User).filter_by(email=email).first()
    if user:
        return user
    user = models.User(email=email, name=name, password_hash=hash_password(DEMO_PASSWORD))
    db.add(user)
    db.flush()
    return user


def seed() -> None:
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        if db.query(models.Event).first() is not None:
            return  # already seeded

        with open(FIXTURES_PATH, encoding="utf-8") as f:
            fixture = json.load(f)

        close_at = _parse_dt(fixture["event"]["submissions_close"])
        open_at = close_at - timedelta(days=30)

        event = models.Event(
            id=fixture["event"]["id"],
            name=fixture["event"]["name"],
            description="Seeded from the DOGFOOD 2026 shared fixtures.",
            submissions_open_at=open_at,
            submissions_close_at=close_at,
        )
        db.add(event)
        db.flush()

        for t in fixture["tracks"]:
            db.add(models.Track(id=t["id"], event_id=event.id, name=t["name"]))
        db.flush()

        # --- Judges -----------------------------------------------------
        judge_users = []
        for j in fixture["judges"]:
            user = _get_or_create_user(db, j["email"], j["name"])
            db.add(models.Role(user_id=user.id, event_id=event.id, role="judge"))
            judge_users.append(user)
        db.flush()

        # --- Teams + participants ----------------------------------------
        for t in fixture["teams"]:
            team = models.Team(
                id=t["id"],
                event_id=event.id,
                name=t["name"],
                invite_token=f"invite-{t['id']}",
            )
            db.add(team)
            db.flush()

            for idx, email in enumerate(t["members"]):
                member = _get_or_create_user(db, email, email.split("@")[0])
                db.add(models.TeamMember(team_id=team.id, user_id=member.id))
                db.add(models.Role(user_id=member.id, event_id=event.id, role="participant"))
        db.flush()

        # --- Projects -----------------------------------------------------
        for p in fixture["projects"]:
            submitted_at = _parse_dt(p["submitted_at"])
            db.add(
                models.Project(
                    id=p["id"],
                    team_id=p["team"],
                    track_id=p.get("track"),
                    title=p["title"],
                    summary=p["summary"],
                    repo_url=p.get("repo_url", ""),
                    status="submitted",
                    submitted_at=submitted_at,
                    updated_at=submitted_at,
                )
            )
        db.flush()

        # --- Checker-facing demo accounts ---------------------------------
        organizer = _get_or_create_user(db, "organizer@dogfood.demo", "Demo Organizer")
        db.add(models.Role(user_id=organizer.id, event_id=event.id, role="organizer"))
        db.add(models.Session(token=TOKEN_ORGANIZER, user_id=organizer.id))

        # judge_a / judge_b in .dogfood.toml map onto two real seeded
        # judges, so T2's peer-score isolation check ("judge_b cannot
        # read judge_a's scores") is testing two genuinely distinct
        # accounts rather than aliases of the same one.
        db.add(models.Session(token=TOKEN_JUDGE_A, user_id=judge_users[0].id))
        db.add(models.Session(token=TOKEN_JUDGE_B, user_id=judge_users[1].id))

        first_team = fixture["teams"][0]
        participant_email = first_team["members"][0]
        participant = db.query(models.User).filter_by(email=participant_email).first()
        db.add(models.Session(token=TOKEN_PARTICIPANT, user_id=participant.id))

        db.commit()
        print(
            f"Seeded: {len(fixture['tracks'])} tracks, {len(fixture['judges'])} judges, "
            f"{len(fixture['teams'])} teams, {len(fixture['projects'])} projects."
        )
        print(f"Checker demo accounts ready (tokens fixed, see .dogfood.toml).")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
