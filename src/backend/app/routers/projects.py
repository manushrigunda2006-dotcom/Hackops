from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DBSession

from .. import models, schemas
from ..auth import require_user
from ..database import get_db
from ..util import iso_z, to_naive_utc, utcnow

router = APIRouter(prefix="/api/projects", tags=["projects"])


def _serialize(project: models.Project, db: DBSession) -> dict:
    team = db.get(models.Team, project.team_id)
    track = db.get(models.Track, project.track_id) if project.track_id else None
    return {
        "id": project.id,
        "team_id": project.team_id,
        "team_name": team.name if team else "",
        "track_id": project.track_id,
        "track_name": track.name if track else None,
        "title": project.title,
        "summary": project.summary,
        "repo_url": project.repo_url,
        "status": project.status,
        "submitted_at": iso_z(project.submitted_at),
        "updated_at": iso_z(project.updated_at),
    }


@router.get("")
def list_projects(db: DBSession = Depends(get_db)):
    """Public gallery. No auth header required — see run.py's
    'gallery is public' check.
    """
    event = db.query(models.Event).order_by(models.Event.created_at.desc()).first()
    projects = []
    if event is not None:
        projects = (
            db.query(models.Project)
            .join(models.Team, models.Team.id == models.Project.team_id)
            .filter(models.Team.event_id == event.id, models.Project.status == "submitted")
            .order_by(models.Project.submitted_at.desc())
            .all()
        )
    return {
        "event": {
            "id": event.id,
            "name": event.name,
            "submissions_close": iso_z(event.submissions_close_at),
        }
        if event
        else None,
        "projects": [_serialize(p, db) for p in projects],
    }


@router.get("/{project_id}")
def get_project(project_id: str, db: DBSession = Depends(get_db)):
    project = db.get(models.Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="No project with that id.")
    return _serialize(project, db)


@router.post("", status_code=201)
def create_project(
    body: schemas.ProjectCreateIn,
    user=Depends(require_user),
    db: DBSession = Depends(get_db),
):
    event = db.query(models.Event).order_by(models.Event.created_at.desc()).first()
    if event is None:
        raise HTTPException(status_code=404, detail="No event to submit to.")

    # Deadline enforcement lives here, in the backend, regardless of
    # what the submit form's disabled-button state shows the user —
    # see run.py's 'closed event refuses submissions' check.
    now = utcnow()
    if now >= to_naive_utc(event.submissions_close_at):
        raise HTTPException(status_code=403, detail="Submissions are closed for this event.")

    team_membership = (
        db.query(models.TeamMember, models.Team)
        .join(models.Team, models.Team.id == models.TeamMember.team_id)
        .filter(models.TeamMember.user_id == user.id, models.Team.event_id == event.id)
        .first()
    )
    if team_membership is None:
        raise HTTPException(
            status_code=403,
            detail="You need to join a team for this event before submitting.",
        )
    _, team = team_membership

    project = models.Project(
        team_id=team.id,
        title=body.title,
        summary=body.summary,
        repo_url=body.repo_url,
        status="submitted",
        submitted_at=now,
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return _serialize(project, db)


@router.patch("/{project_id}")
def update_project(
    project_id: str,
    body: schemas.ProjectCreateIn,
    user=Depends(require_user),
    db: DBSession = Depends(get_db),
):
    """Edit until the deadline — same enforcement as create."""
    project = db.get(models.Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="No project with that id.")

    team = db.get(models.Team, project.team_id)
    is_member = (
        db.query(models.TeamMember)
        .filter_by(team_id=team.id, user_id=user.id)
        .first()
    )
    if is_member is None:
        raise HTTPException(status_code=403, detail="Not a member of this project's team.")

    event = db.get(models.Event, team.event_id)
    if utcnow() >= to_naive_utc(event.submissions_close_at):
        raise HTTPException(status_code=403, detail="Submissions are closed for this event.")

    project.title = body.title
    project.summary = body.summary
    project.repo_url = body.repo_url
    db.commit()
    db.refresh(project)
    return _serialize(project, db)
