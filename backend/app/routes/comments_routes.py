from fastapi import APIRouter, Depends, Request
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
        username=c.user.username,
        display_name=c.user.display_name,
        sector=c.user.sector,
        company=c.user.company,
        city=c.user.city,
        body=c.body,
        created_at=c.created_at,
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
    # Eager-load user
    comment = db.scalar(select(Comment).where(Comment.id == comment.id))
    return _to_out(comment)
