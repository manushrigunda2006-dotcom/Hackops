"""Loads data/fixtures.json into SQLite.

Idempotent seeding for T1 + T2.

T1 data is created on the first boot.
T2 judging data is also created from the fixture scores.

If T1 was already seeded before T2 was implemented, running this
seed function again will add the missing T2 data without deleting
existing T1 data.
"""

import json
import os
from datetime import datetime, timedelta

from sqlalchemy.orm import Session as DBSession

from . import models
from .auth import hash_password
from .database import Base, SessionLocal, engine
from .util import to_naive_utc


FIXTURES_PATH = os.environ.get(
    "DOGFOOD_FIXTURES_PATH",
    "/app/data/fixtures.json",
)

DEMO_PASSWORD = "dogfood"

# Fixed tokens — must match .dogfood.toml [auth].
TOKEN_ORGANIZER = "org_7f2a"
TOKEN_JUDGE_A = "jdg_a_91bc"
TOKEN_JUDGE_B = "jdg_b_44de"
TOKEN_PARTICIPANT = "prt_2e88"


def _parse_dt(s: str) -> datetime:
    return to_naive_utc(
        datetime.fromisoformat(s.replace("Z", "+00:00"))
    )


def _get_or_create_user(
    db: DBSession,
    email: str,
    name: str,
) -> models.User:
    user = db.query(models.User).filter_by(email=email).first()

    if user:
        return user

    user = models.User(
        email=email,
        name=name,
        password_hash=hash_password(DEMO_PASSWORD),
    )

    db.add(user)
    db.flush()

    return user


def _get_or_create_role(
    db: DBSession,
    user_id: str,
    event_id: str,
    role: str,
) -> models.Role:
    role_row = (
        db.query(models.Role)
        .filter_by(
            user_id=user_id,
            event_id=event_id,
            role=role,
        )
        .first()
    )

    if role_row:
        return role_row

    role_row = models.Role(
        user_id=user_id,
        event_id=event_id,
        role=role,
    )

    db.add(role_row)
    db.flush()

    return role_row


T2_RUBRIC_NAMES = [
    "functionality",
    "quality",
    "innovation",
    "values",
]


def _normalize_t2_criteria(criteria: dict) -> dict:
    """
    Return a complete T2 criteria object.

    Older fixture rows contain only functionality, quality, and innovation.
    The published rubric also contains values, so legacy rows get an
    explicit zero for the missing criterion instead of leaving the JSON
    structurally incomplete.
    """
    normalized = {}

    for name in T2_RUBRIC_NAMES:
        value = criteria.get(name, 0)

        try:
            numeric_value = float(value)
        except (TypeError, ValueError):
            numeric_value = 0.0

        normalized[name] = numeric_value

    return normalized


def _seed_t2(
    db: DBSession,
    fixture: dict,
    event: models.Event,
    judge_users: list[models.User],
) -> tuple[int, int, int]:
    """
    Populate T2 judging data.

    Fixture judge IDs such as jdg_01 are converted to the
    real database User IDs before creating or repairing
    JudgeAssignment and JudgeScore rows.

    Legacy score rows that omit the fourth rubric criterion
    ("values") are normalized to an explicit 0 so every seeded
    score matches the published four-criterion rubric.

    Returns:
        assignments_created,
        rubrics_created,
        scores_created
    """

    assignments_created = 0
    rubrics_created = 0
    scores_created = 0

    # ---------------------------------------------------------------
    # Build fixture judge ID -> real database user ID mapping
    # ---------------------------------------------------------------

    judge_id_map: dict[str, str] = {}

    # Use the fixture judge email to find the actual database user.
    # This is safer than relying only on list ordering.
    for fixture_judge in fixture.get("judges", []):
        user = (
            db.query(models.User)
            .filter_by(email=fixture_judge["email"])
            .first()
        )

        if user:
            judge_id_map[fixture_judge["id"]] = user.id

    # Also include the supplied judge_users as a fallback.
    for fixture_judge, db_user in zip(
        fixture.get("judges", []),
        judge_users,
    ):
        judge_id_map.setdefault(
            fixture_judge["id"],
            db_user.id,
        )

    # ---------------------------------------------------------------
    # T2 RUBRIC
    # ---------------------------------------------------------------

    # The fixture scores use these four criteria:
    # functionality
    # quality
    # innovation
    # values

    # We give them equal weights for the seeded demo rubric.

    rubric_names = T2_RUBRIC_NAMES

    for name in rubric_names:
        existing = (
            db.query(models.RubricCriterion)
            .filter_by(
                event_id=event.id,
                name=name,
            )
            .first()
        )

        if existing:
            continue

        db.add(
            models.RubricCriterion(
                event_id=event.id,
                name=name,
                weight=1.0,
                max_score=5.0,
            )
        )

        rubrics_created += 1

    db.flush()

    # ---------------------------------------------------------------
    # T2 SCORES + ASSIGNMENTS
    # ---------------------------------------------------------------

    # The fixture already contains judge/project/criteria/comment
    # records. Convert each fixture score into:
    #
    #   JudgeAssignment
    #   JudgeScore
    #
    # while replacing fixture judge IDs with real database user IDs.

    scores = fixture.get("scores", [])

    for score in scores:
        fixture_judge_id = score["judge"]
        project_id = score["project"]

        # Convert fixture judge ID -> real database user ID.
        real_judge_id = judge_id_map.get(fixture_judge_id)

        # If the judge cannot be resolved, skip this fixture score
        # instead of creating an invalid database reference.
        if not real_judge_id:
            print(
                "Warning: could not map fixture judge "
                f"{fixture_judge_id} to a database user."
            )
            continue

        # -----------------------------------------------------------
        # Repair any old assignment that still contains the fixture ID
        # -----------------------------------------------------------

        old_assignment = (
            db.query(models.JudgeAssignment)
            .filter_by(
                judge_id=fixture_judge_id,
                project_id=project_id,
                event_id=event.id,
            )
            .first()
        )

        # -----------------------------------------------------------
        # Find assignment using REAL judge ID
        # -----------------------------------------------------------

        assignment = (
            db.query(models.JudgeAssignment)
            .filter_by(
                judge_id=real_judge_id,
                project_id=project_id,
                event_id=event.id,
            )
            .first()
        )

        if old_assignment:
            if assignment is None:
                # Repair the legacy row in place.
                old_assignment.judge_id = real_judge_id
                assignment = old_assignment
            elif old_assignment.id != assignment.id:
                # If both legacy and corrected rows exist, keep only
                # the corrected assignment.
                db.delete(old_assignment)
                db.flush()

        if not assignment:
            assignment = models.JudgeAssignment(
                judge_id=real_judge_id,
                project_id=project_id,
                event_id=event.id,
            )

            db.add(assignment)
            db.flush()

            assignments_created += 1

        # -----------------------------------------------------------
        # Repair any old score that still contains the fixture ID
        # -----------------------------------------------------------

        old_score = (
            db.query(models.JudgeScore)
            .filter_by(
                judge_id=fixture_judge_id,
                project_id=project_id,
                event_id=event.id,
            )
            .first()
        )

        existing_score = (
            db.query(models.JudgeScore)
            .filter_by(
                judge_id=real_judge_id,
                project_id=project_id,
                event_id=event.id,
            )
            .first()
        )

        if old_score:
            if existing_score is None:
                old_score.judge_id = real_judge_id
                existing_score = old_score
            else:
                # If both old and corrected records somehow exist,
                # keep the corrected record and remove the duplicate.
                db.delete(old_score)
                db.flush()

        # -----------------------------------------------------------
        # Normalize existing or newly created score criteria
        # -----------------------------------------------------------

        if existing_score:
            try:
                existing_criteria = json.loads(
                    existing_score.criteria_json or "{}"
                )
            except (TypeError, ValueError, json.JSONDecodeError):
                existing_criteria = {}

            normalized_criteria = _normalize_t2_criteria(
                existing_criteria
            )

            if existing_criteria != normalized_criteria:
                existing_score.criteria_json = json.dumps(
                    normalized_criteria
                )

            continue

        fixture_criteria = score.get("criteria", {})
        criteria = _normalize_t2_criteria(fixture_criteria)

        db.add(
            models.JudgeScore(
                judge_id=real_judge_id,
                project_id=project_id,
                event_id=event.id,
                criteria_json=json.dumps(criteria),
                comment=score.get("comment", ""),
                submitted_at=_parse_dt(
                    score.get(
                        "submitted_at",
                        fixture["event"]["submissions_close"],
                    )
                ),
            )
        )

        scores_created += 1

    db.flush()

    return (
        assignments_created,
        rubrics_created,
        scores_created,
    )


def seed() -> None:
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()

    try:
        with open(FIXTURES_PATH, encoding="utf-8") as f:
            fixture = json.load(f)

        # ============================================================
        # T1 SEEDING
        # ============================================================

        event = db.query(models.Event).first()

        if event is None:
            close_at = _parse_dt(
                fixture["event"]["submissions_close"]
            )

            open_at = close_at - timedelta(days=30)

            event = models.Event(
                id=fixture["event"]["id"],
                name=fixture["event"]["name"],
                description=(
                    "Seeded from the DOGFOOD 2026 shared fixtures."
                ),
                submissions_open_at=open_at,
                submissions_close_at=close_at,
            )

            db.add(event)
            db.flush()

            # --------------------------------------------------------
            # Tracks
            # --------------------------------------------------------

            for t in fixture["tracks"]:
                db.add(
                    models.Track(
                        id=t["id"],
                        event_id=event.id,
                        name=t["name"],
                    )
                )

            db.flush()

            # --------------------------------------------------------
            # Judges
            # --------------------------------------------------------

            judge_users = []

            for j in fixture["judges"]:
                user = _get_or_create_user(
                    db,
                    j["email"],
                    j["name"],
                )

                _get_or_create_role(
                    db,
                    user.id,
                    event.id,
                    "judge",
                )

                judge_users.append(user)

            db.flush()

            # --------------------------------------------------------
            # Teams + participants
            # --------------------------------------------------------

            for t in fixture["teams"]:
                existing_team = (
                    db.query(models.Team)
                    .filter_by(id=t["id"])
                    .first()
                )

                if existing_team:
                    team = existing_team
                else:
                    team = models.Team(
                        id=t["id"],
                        event_id=event.id,
                        name=t["name"],
                        invite_token=f"invite-{t['id']}",
                    )

                    db.add(team)
                    db.flush()

                for email in t["members"]:
                    member = _get_or_create_user(
                        db,
                        email,
                        email.split("@")[0],
                    )

                    existing_member = (
                        db.query(models.TeamMember)
                        .filter_by(
                            team_id=team.id,
                            user_id=member.id,
                        )
                        .first()
                    )

                    if not existing_member:
                        db.add(
                            models.TeamMember(
                                team_id=team.id,
                                user_id=member.id,
                            )
                        )

                    _get_or_create_role(
                        db,
                        member.id,
                        event.id,
                        "participant",
                    )

            db.flush()

            # --------------------------------------------------------
            # Projects
            # --------------------------------------------------------

            for p in fixture["projects"]:
                existing_project = (
                    db.query(models.Project)
                    .filter_by(id=p["id"])
                    .first()
                )

                if existing_project:
                    continue

                submitted_at = _parse_dt(
                    p["submitted_at"]
                )

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

        else:
            # Existing database: recover the fixture's judges.
            judge_users = []

            for j in fixture["judges"]:
                user = (
                    db.query(models.User)
                    .filter_by(email=j["email"])
                    .first()
                )

                if user:
                    judge_users.append(user)

                    _get_or_create_role(
                        db,
                        user.id,
                        event.id,
                        "judge",
                    )

            db.flush()

        # ============================================================
        # T2 SEEDING
        # ============================================================

        assignments, rubrics, scores = _seed_t2(
            db,
            fixture,
            event,
            judge_users,
        )

        # ============================================================
        # CHECKER-FACING DEMO ACCOUNTS
        # ============================================================

        organizer = _get_or_create_user(
            db,
            "organizer@dogfood.demo",
            "Demo Organizer",
        )

        _get_or_create_role(
            db,
            organizer.id,
            event.id,
            "organizer",
        )

        existing_session = (
            db.query(models.Session)
            .filter_by(token=TOKEN_ORGANIZER)
            .first()
        )

        if not existing_session:
            db.add(
                models.Session(
                    token=TOKEN_ORGANIZER,
                    user_id=organizer.id,
                )
            )

        # ------------------------------------------------------------
        # Judge A
        # ------------------------------------------------------------

        if len(judge_users) >= 1:
            existing_session = (
                db.query(models.Session)
                .filter_by(token=TOKEN_JUDGE_A)
                .first()
            )

            if not existing_session:
                db.add(
                    models.Session(
                        token=TOKEN_JUDGE_A,
                        user_id=judge_users[0].id,
                    )
                )

        # ------------------------------------------------------------
        # Judge B
        # ------------------------------------------------------------

        if len(judge_users) >= 2:
            existing_session = (
                db.query(models.Session)
                .filter_by(token=TOKEN_JUDGE_B)
                .first()
            )

            if not existing_session:
                db.add(
                    models.Session(
                        token=TOKEN_JUDGE_B,
                        user_id=judge_users[1].id,
                    )
                )

        # ------------------------------------------------------------
        # Participant
        # ------------------------------------------------------------

        if fixture["teams"]:
            first_team = fixture["teams"][0]

            if first_team["members"]:
                participant_email = first_team["members"][0]

                participant = (
                    db.query(models.User)
                    .filter_by(email=participant_email)
                    .first()
                )

                if participant:
                    existing_session = (
                        db.query(models.Session)
                        .filter_by(token=TOKEN_PARTICIPANT)
                        .first()
                    )

                    if not existing_session:
                        db.add(
                            models.Session(
                                token=TOKEN_PARTICIPANT,
                                user_id=participant.id,
                            )
                        )

        db.commit()

        print(
            "T2 seed complete: "
            f"{assignments} assignments, "
            f"{rubrics} rubrics, "
            f"{scores} scores."
        )

    finally:
        db.close()


if __name__ == "__main__":
    seed()
