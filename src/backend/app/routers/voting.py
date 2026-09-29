from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .. import models
from ..database import get_db
from ..auth import get_current_user


router = APIRouter(
    prefix="/api/voting",
    tags=["community voting"],
)


def _get_current_event(db: Session):
    """
    Return the current event.

    The project currently supports one active event at a time,
    so the newest event is used.
    """

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


def _check_voting_window(event: models.Event):
    """
    Make sure community voting is currently open.
    """

    if event.voting_open_at is None:
        raise HTTPException(
            status_code=403,
            detail="Community voting has not been configured.",
        )

    if event.voting_close_at is None:
        raise HTTPException(
            status_code=403,
            detail="Community voting has not been configured.",
        )

    now = datetime.utcnow()

    if now < event.voting_open_at:
        raise HTTPException(
            status_code=403,
            detail="Community voting has not opened yet.",
        )

    if now >= event.voting_close_at:
        raise HTTPException(
            status_code=403,
            detail="Community voting has closed.",
        )


@router.get("/projects")
def get_voting_projects(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """
    Return submitted projects available for community voting.

    Projects are randomized on every request so that projects do not
    always appear in the same order on the ballot.
    """

    event = _get_current_event(db)

    _check_voting_window(event)

    projects = (
        db.query(models.Project)
        .filter(
            models.Project.event_id == event.id,
            models.Project.status == "submitted",
        )
        .order_by(func.random())
        .all()
    )

    return {
        "event_id": event.id,
        "projects": [
            {
                "id": project.id,
                "title": project.title,
                "summary": project.summary,
                "track_id": project.track_id,
                "repo_url": project.repo_url,
            }
            for project in projects
        ],
    }


@router.post("/projects/{project_id}")
def vote_for_project(
    project_id: str,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """
    Cast one community vote for a project.

    The backend enforces:
    - authentication
    - active voting window
    - valid submitted project
    - one vote per user per event
    """

    event = _get_current_event(db)

    _check_voting_window(event)

    project = (
        db.query(models.Project)
        .filter(
            models.Project.id == project_id,
            models.Project.event_id == event.id,
            models.Project.status == "submitted",
        )
        .first()
    )

    if project is None:
        raise HTTPException(
            status_code=404,
            detail="Project is not available for voting.",
        )

    vote = models.CommunityVote(
        event_id=event.id,
        project_id=project.id,
        voter_id=user.id,
    )

    db.add(vote)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()

        raise HTTPException(
            status_code=409,
            detail="You have already voted in this event.",
        )

    return {
        "success": True,
        "message": "Vote recorded successfully.",
        "project_id": project.id,
    }


@router.get("/status")
def get_voting_status(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """
    Return the current user's voting status.
    """

    event = _get_current_event(db)

    now = datetime.utcnow()

    voting_open = (
        event.voting_open_at is not None
        and event.voting_close_at is not None
        and event.voting_open_at <= now < event.voting_close_at
    )

    existing_vote = (
        db.query(models.CommunityVote)
        .filter(
            models.CommunityVote.event_id == event.id,
            models.CommunityVote.voter_id == user.id,
        )
        .first()
    )

    return {
        "event_id": event.id,
        "voting_open": voting_open,
        "has_voted": existing_vote is not None,
    }