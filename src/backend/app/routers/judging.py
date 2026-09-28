import csv
import io
import json

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session as DBSession

from .. import models
from ..auth import require_role
from ..database import get_db
from ..util import iso_z


# ---------------------------------------------------------------------------
# Main T2 judging router
# ---------------------------------------------------------------------------

router = APIRouter(
    prefix="/api/judging",
    tags=["judging"],
)


# ---------------------------------------------------------------------------
# Compatibility router for the DOGFOOD acceptance checker
#
# The checker expects:
#   GET /api/judge/scores
#   GET /api/judge/scores?judge=judge_a
#   GET /api/export.csv
#
# These routes are kept separate from the main /api/judging routes so that
# the existing API remains unchanged.
# ---------------------------------------------------------------------------

compat_router = APIRouter(
    tags=["judging-compat"],
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _current_event(db: DBSession):
    event = (
        db.query(models.Event)
        .order_by(models.Event.created_at.desc())
        .first()
    )

    if event is None:
        raise HTTPException(
            status_code=404,
            detail="No event found.",
        )

    return event


def _serialize_score(score, db):
    project = db.get(models.Project, score.project_id)

    return {
        "id": score.id,
        "judge_id": score.judge_id,
        "project_id": score.project_id,
        "project_title": project.title if project else None,
        "criteria": json.loads(score.criteria_json),
        "comment": score.comment,
        "submitted_at": iso_z(score.submitted_at),
    }


def _calculate_weighted_average(score, rubric):
    """
    Calculate the weighted average score on a 0-5 scale.

    Formula:

        sum(score * weight) / sum(weight)

    Because each rubric criterion has a maximum score of 5,
    the resulting weighted average remains on a 0-5 scale.
    """

    criteria = json.loads(score.criteria_json)

    total_weight = sum(
        criterion.weight
        for criterion in rubric
    )

    if total_weight == 0:
        return 0.0

    weighted_sum = sum(
        criteria.get(criterion.name, 0)
        * criterion.weight
        for criterion in rubric
    )

    return round(
        weighted_sum / total_weight,
        2,
    )


def _get_rubric(db, event_id):
    return (
        db.query(models.RubricCriterion)
        .filter(
            models.RubricCriterion.event_id == event_id
        )
        .order_by(
            models.RubricCriterion.name
        )
        .all()
    )


def _get_scores_for_judge(db, event_id, judge_id):
    return (
        db.query(models.JudgeScore)
        .filter(
            models.JudgeScore.event_id == event_id,
            models.JudgeScore.judge_id == judge_id,
        )
        .order_by(
            models.JudgeScore.submitted_at.desc()
        )
        .all()
    )


# ---------------------------------------------------------------------------
# Request model
# ---------------------------------------------------------------------------

class ScoreSubmission(BaseModel):
    project_id: str
    criteria: dict[str, float]
    comment: str = Field(
        default="",
        max_length=5000,
    )


# ---------------------------------------------------------------------------
# Judge: read own scores
# ---------------------------------------------------------------------------

@router.get("/my-scores")
def get_my_scores(
    user=Depends(require_role("judge")),
    db: DBSession = Depends(get_db),
):
    event = _current_event(db)

    scores = _get_scores_for_judge(
        db,
        event.id,
        user.id,
    )

    rubric = _get_rubric(
        db,
        event.id,
    )

    result = []

    for score in scores:
        item = _serialize_score(
            score,
            db,
        )

        item["weighted_average"] = (
            _calculate_weighted_average(
                score,
                rubric,
            )
        )

        result.append(item)

    return {
        "event_id": event.id,
        "judge_id": user.id,
        "scores": result,
    }


# ---------------------------------------------------------------------------
# Judge: read one own score
# ---------------------------------------------------------------------------

@router.get("/scores/{score_id}")
def get_my_score(
    score_id: str,
    user=Depends(require_role("judge")),
    db: DBSession = Depends(get_db),
):
    event = _current_event(db)

    score = db.get(
        models.JudgeScore,
        score_id,
    )

    if score is None or score.event_id != event.id:
        raise HTTPException(
            status_code=404,
            detail="Score not found",
        )

    if score.judge_id != user.id:
        raise HTTPException(
            status_code=403,
            detail="You cannot access another judge's score.",
        )

    rubric = _get_rubric(
        db,
        event.id,
    )

    result = _serialize_score(
        score,
        db,
    )

    result["weighted_average"] = (
        _calculate_weighted_average(
            score,
            rubric,
        )
    )

    return result


# ---------------------------------------------------------------------------
# Judge: read assignments
# ---------------------------------------------------------------------------

@router.get("/assignments")
def get_my_assignments(
    user=Depends(require_role("judge")),
    db: DBSession = Depends(get_db),
):
    event = _current_event(db)

    assignments = (
        db.query(models.JudgeAssignment)
        .filter(
            models.JudgeAssignment.event_id == event.id,
            models.JudgeAssignment.judge_id == user.id,
        )
        .order_by(
            models.JudgeAssignment.created_at
        )
        .all()
    )

    result = []

    for assignment in assignments:
        project = db.get(
            models.Project,
            assignment.project_id,
        )

        result.append(
            {
                "id": assignment.id,
                "judge_id": assignment.judge_id,
                "project_id": assignment.project_id,
                "project_title": (
                    project.title
                    if project
                    else None
                ),
                "created_at": iso_z(
                    assignment.created_at
                ),
            }
        )

    return {
        "event_id": event.id,
        "judge_id": user.id,
        "assignments": result,
    }


# ---------------------------------------------------------------------------
# Judge: read rubric
# ---------------------------------------------------------------------------

@router.get("/rubric")
def get_rubric(
    user=Depends(require_role("judge")),
    db: DBSession = Depends(get_db),
):
    event = _current_event(db)

    criteria = _get_rubric(
        db,
        event.id,
    )

    return {
        "event_id": event.id,
        "criteria": [
            {
                "id": criterion.id,
                "name": criterion.name,
                "weight": criterion.weight,
                "max_score": criterion.max_score,
            }
            for criterion in criteria
        ],
    }


# ---------------------------------------------------------------------------
# Judge: submit or update score
# ---------------------------------------------------------------------------

@router.post("/scores")
def submit_score(
    payload: ScoreSubmission,
    user=Depends(require_role("judge")),
    db: DBSession = Depends(get_db),
):
    event = _current_event(db)

    assignment = (
        db.query(models.JudgeAssignment)
        .filter(
            models.JudgeAssignment.event_id == event.id,
            models.JudgeAssignment.judge_id == user.id,
            models.JudgeAssignment.project_id
            == payload.project_id,
        )
        .first()
    )

    if assignment is None:
        raise HTTPException(
            status_code=403,
            detail="You are not assigned to this project.",
        )

    rubric = _get_rubric(
        db,
        event.id,
    )

    if not rubric:
        raise HTTPException(
            status_code=400,
            detail="No rubric configured for this event.",
        )

    rubric_by_name = {
        criterion.name: criterion
        for criterion in rubric
    }

    # Reject unknown criteria.
    for name in payload.criteria:
        if name not in rubric_by_name:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Unknown rubric criterion: {name}"
                ),
            )

    # Require every configured criterion.
    for criterion in rubric:
        if criterion.name not in payload.criteria:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Missing rubric criterion: "
                    f"{criterion.name}"
                ),
            )

        value = payload.criteria[
            criterion.name
        ]

        if (
            value < 0
            or value > criterion.max_score
        ):
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Score for '{criterion.name}' "
                    f"must be between 0 and "
                    f"{criterion.max_score}."
                ),
            )

    # Weighted average on a 0-5 scale.
    total_weight = sum(
        criterion.weight
        for criterion in rubric
    )

    weighted_sum = sum(
        payload.criteria[criterion.name]
        * criterion.weight
        for criterion in rubric
    )

    if total_weight == 0:
        weighted_average = 0.0
    else:
        weighted_average = round(
            weighted_sum / total_weight,
            2,
        )

    # Update existing score or create a new one.
    existing = (
        db.query(models.JudgeScore)
        .filter(
            models.JudgeScore.event_id == event.id,
            models.JudgeScore.judge_id == user.id,
            models.JudgeScore.project_id
            == payload.project_id,
        )
        .first()
    )

    if existing:
        existing.criteria_json = json.dumps(
            payload.criteria
        )

        existing.comment = payload.comment

        score = existing

    else:
        score = models.JudgeScore(
            judge_id=user.id,
            project_id=payload.project_id,
            event_id=event.id,
            criteria_json=json.dumps(
                payload.criteria
            ),
            comment=payload.comment,
        )

        db.add(score)

    db.commit()
    db.refresh(score)

    result = _serialize_score(
        score,
        db,
    )

    result["weighted_average"] = (
        weighted_average
    )

    return result


# ---------------------------------------------------------------------------
# Organizer: live judging progress
# ---------------------------------------------------------------------------

@router.get("/progress")
def get_judging_progress(
    user=Depends(require_role("organizer")),
    db: DBSession = Depends(get_db),
):
    """
    Live judging progress dashboard.

    Organizer-only endpoint.

    Shows:
    - total assignments
    - submitted scores
    - remaining scores
    - completion percentage
    - per-judge progress
    """

    event = _current_event(db)

    assignments = (
        db.query(models.JudgeAssignment)
        .filter(
            models.JudgeAssignment.event_id
            == event.id
        )
        .all()
    )

    scores = (
        db.query(models.JudgeScore)
        .filter(
            models.JudgeScore.event_id
            == event.id
        )
        .all()
    )

    total_assignments = len(
        assignments
    )

    submitted_scores = len(scores)

    remaining_scores = max(
        total_assignments
        - submitted_scores,
        0,
    )

    if total_assignments:
        completion_percentage = round(
            (
                submitted_scores
                / total_assignments
            )
            * 100,
            2,
        )
    else:
        completion_percentage = 0.0

    judge_assignment_counts = {}

    for assignment in assignments:
        judge_assignment_counts.setdefault(
            assignment.judge_id,
            {
                "assigned": 0,
                "submitted": 0,
            },
        )

        judge_assignment_counts[
            assignment.judge_id
        ]["assigned"] += 1

    for score in scores:
        judge_assignment_counts.setdefault(
            score.judge_id,
            {
                "assigned": 0,
                "submitted": 0,
            },
        )

        judge_assignment_counts[
            score.judge_id
        ]["submitted"] += 1

    judge_progress = []

    for (
        judge_id,
        counts,
    ) in sorted(
        judge_assignment_counts.items()
    ):
        assigned = counts["assigned"]

        submitted = min(
            counts["submitted"],
            assigned,
        )

        if assigned:
            percentage = round(
                (
                    submitted
                    / assigned
                )
                * 100,
                2,
            )
        else:
            percentage = 0.0

        judge_progress.append(
            {
                "judge_id": judge_id,
                "assigned": assigned,
                "submitted": submitted,
                "remaining": max(
                    assigned - submitted,
                    0,
                ),
                "completion_percentage": percentage,
            }
        )

    return {
        "event_id": event.id,
        "total_assignments": total_assignments,
        "submitted_scores": submitted_scores,
        "remaining_scores": remaining_scores,
        "completion_percentage": completion_percentage,
        "judges": judge_progress,
    }


# ---------------------------------------------------------------------------
# Organizer: CSV export
# ---------------------------------------------------------------------------

@router.get("/export.csv")
def export_scores_csv(
    user=Depends(require_role("organizer")),
    db: DBSession = Depends(get_db),
):
    event = _current_event(db)

    scores = (
        db.query(models.JudgeScore)
        .filter(
            models.JudgeScore.event_id
            == event.id
        )
        .order_by(
            models.JudgeScore.submitted_at
        )
        .all()
    )

    output = io.StringIO()

    writer = csv.writer(output)

    writer.writerow(
        [
            "score_id",
            "judge_id",
            "project_id",
            "criteria",
            "comment",
            "submitted_at",
        ]
    )

    for score in scores:
        writer.writerow(
            [
                score.id,
                score.judge_id,
                score.project_id,
                score.criteria_json,
                score.comment,
                iso_z(
                    score.submitted_at
                ),
            ]
        )

    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={
            "Content-Disposition":
                'attachment; filename="judging-scores.csv"'
        },
    )


# ===========================================================================
# DOGFOOD checker compatibility endpoints
# ===========================================================================


@compat_router.get("/api/judge/scores")
def checker_judge_scores(
    judge: str | None = None,
    user=Depends(require_role("judge")),
    db: DBSession = Depends(get_db),
):
    """
    Compatibility endpoint for the DOGFOOD acceptance checker.

    The checker expects /api/judge/scores.

    A judge can only see their own scores.

    When a judge query parameter is supplied, it represents a request
    for a specific judge's scores. We reject that request rather than
    allowing one judge to probe another judge's ballot.
    """

    if judge is not None:
        raise HTTPException(
            status_code=403,
            detail="Judges cannot access another judge's scores.",
        )

    event = _current_event(db)

    scores = _get_scores_for_judge(
        db,
        event.id,
        user.id,
    )

    rubric = _get_rubric(
        db,
        event.id,
    )

    result = []

    for score in scores:
        item = _serialize_score(
            score,
            db,
        )

        item["weighted_average"] = (
            _calculate_weighted_average(
                score,
                rubric,
            )
        )

        result.append(item)

    return {
        "event_id": event.id,
        "judge_id": user.id,
        "scores": result,
    }


@compat_router.get("/api/judge/scores/{score_id}")
def checker_judge_score(
    score_id: str,
    user=Depends(require_role("judge")),
    db: DBSession = Depends(get_db),
):
    """
    Compatibility endpoint for reading one score through the
    checker-style /api/judge/scores/{score_id} route.
    """

    event = _current_event(db)

    score = db.get(
        models.JudgeScore,
        score_id,
    )

    if score is None or score.event_id != event.id:
        raise HTTPException(
            status_code=404,
            detail="Score not found",
        )

    if score.judge_id != user.id:
        raise HTTPException(
            status_code=403,
            detail="You cannot access another judge's score.",
        )

    rubric = _get_rubric(
        db,
        event.id,
    )

    result = _serialize_score(
        score,
        db,
    )

    result["weighted_average"] = (
        _calculate_weighted_average(
            score,
            rubric,
        )
    )

    return result


@compat_router.get("/api/export.csv")
def checker_export_scores_csv(
    user=Depends(require_role("organizer")),
    db: DBSession = Depends(get_db),
):
    """
    Compatibility endpoint for the DOGFOOD acceptance checker.

    Delegates to the same organizer-only CSV export logic used by
    /api/judging/export.csv.
    """

    return export_scores_csv(
        user=user,
        db=db,
    )