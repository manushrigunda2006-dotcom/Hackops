from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DBSession

from .. import models, schemas
from ..auth import require_user
from ..database import get_db

router = APIRouter(prefix="/api/teams", tags=["teams"])


@router.post("/join", response_model=schemas.TeamOut)
def join_team(
    body: schemas.TeamJoinIn,
    user=Depends(require_user),
    db: DBSession = Depends(get_db),
):
    team = db.query(models.Team).filter_by(invite_token=body.invite_token.strip()).first()
    if team is None:
        raise HTTPException(status_code=404, detail="That invite code doesn't match any team.")

    already = (
        db.query(models.TeamMember)
        .filter_by(team_id=team.id, user_id=user.id)
        .first()
    )
    if already is None:
        db.add(models.TeamMember(team_id=team.id, user_id=user.id))
        # Joining a team makes you a participant in that team's event,
        # unless you already hold a role there (e.g. you're also the
        # organizer testing your own invite link).
        has_role = (
            db.query(models.Role)
            .filter_by(user_id=user.id, event_id=team.event_id)
            .first()
        )
        if has_role is None:
            db.add(models.Role(user_id=user.id, event_id=team.event_id, role="participant"))
        db.commit()

    return schemas.TeamOut(id=team.id, name=team.name, event_id=team.event_id)
