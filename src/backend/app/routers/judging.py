import csv
import io
import json

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session as DBSession

from .. import models
from ..auth import require_role
from ..database import get_db
from ..util import iso_z


router = APIRouter(
    prefix="/api/judging",
    tags=["judging"],
)


def _current_event(db: DBSession) -> models.Event:
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


def _serialize_score(
    score: models.JudgeScore,
    db: DBSession,
) -> dict:
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


@router.get("/my-scores")
def get_my_scores(
    user=Depends(require_role("judge")),
    db: DBSession = Depends(get_db),
):
    """
    Return only the scores belonging to the currently authenticated judge.

    The judge_id filter is enforced by the backend.
    """

    event = _current_event(db)

    scores = (
        db.query(models.JudgeScore)
        .filter(
            models.JudgeScore.event_id == event.id,
            models.JudgeScore.judge_id == user.id,
        )
        .order_by(models.JudgeScore.submitted_at.desc())
        .all()
    )

    return {
        "event_id": event.id,
        "judge_id": user.id,
        "scores": [
            _serialize_score(score, db)
            for score in scores
        ],
    }


@router.get("/scores/{score_id}")
def get_my_score(
    score_id: str,
    user=Depends(require_role("judge")),
    db: DBSession = Depends(get_db),
):
    """
    Return one score only if it belongs to the current judge.

    A judge cannot use this endpoint to read another judge's score.
    """

    event = _current_event(db)

    score = db.get(models.JudgeScore, score_id)

    if score is None or score.event_id != event.id:
        raise HTTPException(
            status_code=404,
            detail="Score not found.",
        )

    if score.judge_id != user.id:
        raise HTTPException(
            status_code=403,
            detail="You cannot access another judge's score.",
        )

    return _serialize_score(score, db)


@router.get("/assignments")
def get_my_assignments(
    user=Depends(require_role("judge")),
    db: DBSession = Depends(get_db),
):
    """
    Return only assignments belonging to the current judge.
    """

    event = _current_event(db)

    assignments = (
        db.query(models.JudgeAssignment)
        .filter(
            models.JudgeAssignment.event_id == event.id,
            models.JudgeAssignment.judge_id == user.id,
        )
        .order_by(models.JudgeAssignment.created_at)
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


@router.get("/rubric")
def get_rubric(
    user=Depends(require_role("judge")),
    db: DBSession = Depends(get_db),
):
    """
    Return the organizer-configured rubric for judges.
    """

    event = _current_event(db)

    criteria = (
        db.query(models.RubricCriterion)
        .filter(
            models.RubricCriterion.event_id == event.id
        )
        .order_by(models.RubricCriterion.name)
        .all()
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


@router.get("/export.csv")
def export_scores_csv(
    user=Depends(require_role("organizer")),
    db: DBSession = Depends(get_db),
):
    """
    Organizer-only CSV export of all judging scores.
    """

    event = _current_event(db)

    scores = (
        db.query(models.JudgeScore)
        .filter(
            models.JudgeScore.event_id == event.id
        )
        .order_by(models.JudgeScore.submitted_at)
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
                iso_z(score.submitted_at),
            ]
        )

    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={
            "Content-Disposition": (
                'attachment; filename="judging-scores.csv"'
            )
        },
    )
