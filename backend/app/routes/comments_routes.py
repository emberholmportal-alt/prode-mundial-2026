from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..database import get_db
from ..limiter import limiter
from ..models import Comment, User
from ..schemas import CommentIn, CommentOut

router = APIRouter(prefix="/comments", tags=["comments"])


def _to_out(c: Comment) -> CommentOut:
    return CommentOut(
        id=c.id,
        user_id=c.user_id,
        username=c.user.username,
        display_name=c.user.display_name,
        sector=c.user.sector,
        company=c.user.company,
        city=c.user.city,
        body=c.body,
        created_at=c.created_at,
        updated_at=c.updated_at,
    )


def _load_with_user(db: Session, comment_id: int) -> Comment | None:
    return db.scalar(select(Comment).where(Comment.id == comment_id))


def _check_can_modify(comment: Comment, user: User) -> None:
    if comment.user_id != user.id and not user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="No tenés permiso para modificar este comentario",
        )


@router.get("", response_model=list[CommentOut])
@limiter.limit("60/minute")
def list_comments(
    request: Request,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    limit = max(1, min(limit, 200))
    rows = db.scalars(
        select(Comment).join(User).order_by(desc(Comment.created_at)).limit(limit)
    ).all()
    return [_to_out(c) for c in rows]


@router.post("", response_model=CommentOut, status_code=201)
@limiter.limit("20/minute")
def create_comment(
    request: Request,
    payload: CommentIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    body = payload.body.strip()
    comment = Comment(user_id=user.id, body=body)
    db.add(comment)
    db.commit()
    db.refresh(comment)
    comment = _load_with_user(db, comment.id)
    return _to_out(comment)


@router.patch("/{comment_id}", response_model=CommentOut)
@limiter.limit("30/minute")
def update_comment(
    request: Request,
    comment_id: int,
    payload: CommentIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    comment = _load_with_user(db, comment_id)
    if comment is None:
        raise HTTPException(status_code=404, detail="Comentario no encontrado")
    _check_can_modify(comment, user)
    comment.body = payload.body.strip()
    comment.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(comment)
    return _to_out(comment)


@router.delete("/{comment_id}", status_code=204)
@limiter.limit("30/minute")
def delete_comment(
    request: Request,
    comment_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    comment = db.get(Comment, comment_id)
    if comment is None:
        raise HTTPException(status_code=404, detail="Comentario no encontrado")
    _check_can_modify(comment, user)
    db.delete(comment)
    db.commit()
