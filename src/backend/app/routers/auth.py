from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session as DBSession

from .. import models, schemas
from ..auth import (
    COOKIE_KW,
    create_session,
    get_current_user,
    hash_password,
    verify_password,
)
from ..database import get_db

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login")
def login(body: schemas.LoginIn, response: Response, db: DBSession = Depends(get_db)):
    user = db.query(models.User).filter_by(email=body.email).first()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    token = create_session(db, user.id)
    response.set_cookie("session", token, **COOKIE_KW)
    return {"ok": True}

@router.post("/register")
def register(
    body: schemas.RegisterIn,
    response: Response,
    db: DBSession = Depends(get_db),
):
    email = body.email.strip().lower()
    name = body.name.strip()

    if not name:
        raise HTTPException(
            status_code=400,
            detail="Name is required.",
        )

    if len(body.password) < 6:
        raise HTTPException(
            status_code=400,
            detail="Password must be at least 6 characters.",
        )

    existing_user = (
        db.query(models.User)
        .filter_by(email=email)
        .first()
    )

    if existing_user:
        raise HTTPException(
            status_code=409,
            detail="An account with this email already exists.",
        )

    user = models.User(
        email=email,
        name=name,
        password_hash=hash_password(body.password),
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_session(db, user.id)

    response.set_cookie(
        "session",
        token,
        **COOKIE_KW,
    )

    return {
        "ok": True,
        "user": {
            "id": user.id,
            "email": user.email,
            "name": user.name,
        },
    }

@router.post("/logout")
def logout(response: Response, user=Depends(get_current_user)):
    response.delete_cookie("session", path="/")
    return {"ok": True}


@router.get("/me", response_model=schemas.MeOut)
def me(user=Depends(get_current_user), db: DBSession = Depends(get_db)):
    if user is None:
        raise HTTPException(status_code=401, detail="Not logged in.")
    roles = db.query(models.Role).filter_by(user_id=user.id).all()
    return schemas.MeOut(
        id=user.id,
        email=user.email,
        name=user.name,
        roles=[{"event_id": r.event_id, "role": r.role} for r in roles],
    )
