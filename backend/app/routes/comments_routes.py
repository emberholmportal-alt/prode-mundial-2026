from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from ..auth import get_current_user, oauth2_scheme, _decode_token
from ..database import get_db
from ..limiter import limiter
from ..models import Comment, CommentLike, User
from ..schemas import CommentIn, CommentLikerOut, CommentOut

router = APIRouter(prefix="/comments", tags=["comments"])


def _try_current_user_id(
    token: Optional[str], db: Session
) -> Optional[int]:
    """Devuelve el user.id del que llama si manda un token válido, sino None.
    No falla con 401 si no hay token: las lecturas del feed son públicas y
    solo enriquecemos `liked_by_me` cuando hay sesión."""
    if not token:
        return None
    try:
        payload = _decode_token(token)
    except HTTPException:
        return None
    sub = payload.get("sub")
    if sub is None:
        return None
    user = db.scalar(select(User).where(User.id == int(sub)))
    return user.id if user else None


def _to_out(c: Comment, likes_count: int = 0, liked_by_me: bool = False) -> CommentOut:
    return CommentOut(
        id=c.id,
        user_id=c.user_id,
        username=c.user.username,
        display_name=c.user.display_name,
        sector=c.user.sector,
        company=c.user.company,
        city=c.user.city,
        is_admin=bool(c.user.is_admin),
        body=c.body,
        parent_id=c.parent_id,
        highlighted=bool(c.highlighted),
        likes_count=likes_count,
        liked_by_me=liked_by_me,
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
    limit: int = 200,
    db: Session = Depends(get_db),
    token: Optional[str] = Depends(oauth2_scheme),
):
    limit = max(1, min(limit, 500))
    rows = db.scalars(
        select(Comment).join(User, Comment.user_id == User.id)
        .order_by(desc(Comment.created_at)).limit(limit)
    ).all()

    # Contadores de likes por comment_id (sola query)
    if rows:
        ids = [c.id for c in rows]
        counts_stmt = (
            select(CommentLike.comment_id, func.count(CommentLike.user_id))
            .where(CommentLike.comment_id.in_(ids))
            .group_by(CommentLike.comment_id)
        )
        counts = {cid: int(n) for cid, n in db.execute(counts_stmt).all()}
        # Likes del usuario actual (si está autenticado)
        my_id = _try_current_user_id(token, db)
        if my_id is not None:
            my_liked_stmt = (
                select(CommentLike.comment_id)
                .where(CommentLike.user_id == my_id)
                .where(CommentLike.comment_id.in_(ids))
            )
            my_liked = {cid for (cid,) in db.execute(my_liked_stmt).all()}
        else:
            my_liked = set()
    else:
        counts = {}
        my_liked = set()

    return [_to_out(c, counts.get(c.id, 0), c.id in my_liked) for c in rows]


@router.post("", response_model=CommentOut, status_code=201)
@limiter.limit("20/minute")
def create_comment(
    request: Request,
    payload: CommentIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if payload.parent_id is not None:
        parent = db.get(Comment, payload.parent_id)
        if parent is None:
            raise HTTPException(status_code=404, detail="Comentario padre no encontrado")
    body = payload.body.strip()
    comment = Comment(user_id=user.id, body=body, parent_id=payload.parent_id)
    db.add(comment)
    db.commit()
    db.refresh(comment)
    comment = _load_with_user(db, comment.id)
    return _to_out(comment, 0, False)


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
    # Re-armar el likes_count y liked_by_me
    cnt = db.scalar(
        select(func.count(CommentLike.user_id)).where(CommentLike.comment_id == comment.id)
    ) or 0
    mine = db.scalar(
        select(CommentLike.comment_id)
        .where(CommentLike.comment_id == comment.id, CommentLike.user_id == user.id)
    )
    return _to_out(comment, int(cnt), mine is not None)


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
    db.delete(comment)  # cascade borra respuestas y likes
    db.commit()


@router.post("/{comment_id}/highlight", response_model=CommentOut)
@limiter.limit("60/minute")
def toggle_highlight(
    request: Request,
    comment_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Marca/desmarca un comentario como destacado (recuadro verde). Solo admin."""
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Solo un admin puede destacar comentarios")
    comment = _load_with_user(db, comment_id)
    if comment is None:
        raise HTTPException(status_code=404, detail="Comentario no encontrado")
    comment.highlighted = not bool(comment.highlighted)
    db.commit()
    db.refresh(comment)
    cnt = db.scalar(
        select(func.count(CommentLike.user_id)).where(CommentLike.comment_id == comment.id)
    ) or 0
    mine = db.scalar(
        select(CommentLike.comment_id)
        .where(CommentLike.comment_id == comment.id, CommentLike.user_id == user.id)
    )
    return _to_out(comment, int(cnt), mine is not None)


@router.post("/{comment_id}/like", status_code=204)
@limiter.limit("60/minute")
def like_comment(
    request: Request,
    comment_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    comment = db.get(Comment, comment_id)
    if comment is None:
        raise HTTPException(status_code=404, detail="Comentario no encontrado")
    existing = db.get(CommentLike, (comment_id, user.id))
    if existing is not None:
        return  # idempotente
    db.add(CommentLike(comment_id=comment_id, user_id=user.id))
    db.commit()


@router.delete("/{comment_id}/like", status_code=204)
@limiter.limit("60/minute")
def unlike_comment(
    request: Request,
    comment_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    existing = db.get(CommentLike, (comment_id, user.id))
    if existing is None:
        return  # idempotente
    db.delete(existing)
    db.commit()


@router.get("/{comment_id}/likes", response_model=list[CommentLikerOut])
@limiter.limit("60/minute")
def list_likers(
    request: Request,
    comment_id: int,
    db: Session = Depends(get_db),
):
    if db.get(Comment, comment_id) is None:
        raise HTTPException(status_code=404, detail="Comentario no encontrado")
    stmt = (
        select(
            User.username,
            User.display_name,
            User.company,
            User.city,
            CommentLike.created_at,
        )
        .join(CommentLike, CommentLike.user_id == User.id)
        .where(CommentLike.comment_id == comment_id)
        .order_by(CommentLike.created_at.asc())
    )
    rows = db.execute(stmt).all()
    return [
        CommentLikerOut(
            username=r.username,
            display_name=r.display_name,
            company=r.company,
            city=r.city,
            created_at=r.created_at,
        )
        for r in rows
    ]
