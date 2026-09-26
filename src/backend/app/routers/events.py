from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DBSession

from .. import models, schemas
from ..auth import require_user
from ..database import get_db
from ..util import iso_z, to_naive_utc

router = APIRouter(prefix="/api/events", tags=["events"])


def _out(event: models.Event) -> schemas.EventOut:
    return schemas.EventOut(
        id=event.id,
        name=event.name,
        description=event.description,
        submissions_open_at=iso_z(event.submissions_open_at),
        submissions_close_at=iso_z(event.submissions_close_at),
    )


@router.get("/current", response_model=schemas.EventOut)
def current_event(db: DBSession = Depends(get_db)):
    """The event the gallery/submit flow is scoped to. T1 runs a single
    active event (the seeded fixture event, or the newest one a user
    has created) — see the 'one active event' note in ARCHITECTURE.md.
    """
    event = db.query(models.Event).order_by(models.Event.created_at.desc()).first()
    if event is None:
        raise HTTPException(status_code=404, detail="No event yet.")
    return _out(event)


@router.post("", response_model=schemas.EventOut, status_code=201)
def create_event(
    body: schemas.EventCreateIn,
    user=Depends(require_user),
    db: DBSession = Depends(get_db),
):
    # body's datetimes may arrive naive (an HTML datetime-local input
    # sends no offset) or aware (a direct API call with one) — normalize
    # either way before storing, same convention as everywhere else.
    event = models.Event(
        name=body.name,
        submissions_open_at=to_naive_utc(body.submissions_open_at),
        submissions_close_at=to_naive_utc(body.submissions_close_at),
        created_by=user.id,
    )
    db.add(event)
    db.flush()  # get event.id before creating dependent rows

    for track_name in body.tracks:
        db.add(models.Track(event_id=event.id, name=track_name))

    # Whoever creates an event becomes its organizer. Roles are scoped
    # per-event (see DATA-MODEL.md), so this doesn't touch any role
    # this user holds on other events.
    db.add(models.Role(user_id=user.id, event_id=event.id, role="organizer"))
    db.commit()
    db.refresh(event)
    return _out(event)
