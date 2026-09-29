from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DBSession

from .. import models, schemas
from ..auth import require_user
from ..database import get_db
from ..util import iso_z


router = APIRouter(
    prefix="/api/comments",
    tags=["comments"],
)


def _serialize_comment(
    comment: models.ProjectComment,
    db: DBSession,
) -> dict:
    user = db.get(models.User, comment.user_id)

    return {
        "id": comment.id,
        "project_id": comment.project_id,
        "user_id": comment.user_id,
        "user_name": user.name if user else "Unknown user",
        "content": comment.content,
        "created_at": iso_z(comment.created_at),
    }


@router.get("/projects/{project_id}")
def list_project_comments(
    project_id: str,
    db: DBSession = Depends(get_db),
):
    """
    Publicly read comments attached to a project.
    """

    project = db.get(models.Project, project_id)

    if project is None:
        raise HTTPException(
            status_code=404,
            detail="No project with that id.",
        )

    comments = (
        db.query(models.ProjectComment)
        .filter(
            models.ProjectComment.project_id == project_id
        )
        .order_by(
            models.ProjectComment.created_at.asc()
        )
        .all()
    )

    return {
        "project_id": project_id,
        "comments": [
            _serialize_comment(comment, db)
            for comment in comments
        ],
    }


@router.post(
    "/projects/{project_id}",
    status_code=201,
)
def create_project_comment(
    project_id: str,
    body: schemas.CommentCreateIn,
    user=Depends(require_user),
    db: DBSession = Depends(get_db),
):
    """
    Add an authenticated user's comment to a project.
    """

    project = db.get(
        models.Project,
        project_id,
    )

    if project is None:
        raise HTTPException(
            status_code=404,
            detail="No project with that id.",
        )

    content = body.content.strip()

    if not content:
        raise HTTPException(
            status_code=400,
            detail="Comment cannot be empty.",
        )

    if len(content) > 2000:
        raise HTTPException(
            status_code=400,
            detail="Comment cannot exceed 2000 characters.",
        )

    comment = models.ProjectComment(
        project_id=project_id,
        user_id=user.id,
        content=content,
    )

    db.add(comment)
    db.commit()
    db.refresh(comment)

    return _serialize_comment(
        comment,
        db,
    )