from datetime import datetime
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


COMPANIES = ("grupo_gestion", "carrefour")
CITIES = ("isidro_casanova", "esteban_echeverria")


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("dni", name="uq_users_dni"),
        UniqueConstraint("email", name="uq_users_email"),
        CheckConstraint(
            "company IN ('grupo_gestion', 'carrefour')",
            name="ck_users_company",
        ),
        CheckConstraint(
            "city IN ('isidro_casanova', 'esteban_echeverria')",
            name="ck_users_city",
        ),
        Index("ix_users_company", "company"),
        Index("ix_users_city", "city"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    must_change_password: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    dni: Mapped[str] = mapped_column(String(10), nullable=False)
    email: Mapped[str] = mapped_column(String(200), nullable=False)
    sector: Mapped[str] = mapped_column(String(100), nullable=False)
    company: Mapped[str] = mapped_column(String(20), nullable=False)
    city: Mapped[str] = mapped_column(String(30), nullable=False)
    avatar_config: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), nullable=False, server_default=func.now()
    )

    predictions: Mapped[list["Prediction"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )
    final_pick: Mapped["FinalPick | None"] = relationship(
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True, uselist=False
    )
    comments: Mapped[list["Comment"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )


class Prediction(Base):
    __tablename__ = "predictions"
    __table_args__ = (
        UniqueConstraint("user_id", "match_id", name="uq_predictions_user_match"),
        CheckConstraint("home_score >= 0 AND home_score <= 20", name="ck_predictions_home_range"),
        CheckConstraint("away_score >= 0 AND away_score <= 20", name="ck_predictions_away_range"),
        Index("ix_predictions_match_id", "match_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    match_id: Mapped[str] = mapped_column(String(10), nullable=False)
    home_score: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    away_score: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    # TLA del equipo que pasa por penales — solo aplica para eliminatorias
    # con empate después de 90' + alargue. Null en grupos / no-empate.
    penalty_winner: Mapped[str | None] = mapped_column(String(3), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    user: Mapped[User] = relationship(back_populates="predictions")


class OfficialResult(Base):
    __tablename__ = "official_results"

    match_id: Mapped[str] = mapped_column(String(10), primary_key=True)
    # home_score / away_score = marcador después de 90' + alargue (sin penales).
    home_score: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    away_score: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    # TLA del equipo que ganó por penales — solo aplica para eliminatorias
    # que terminaron empatadas en 90' + alargue.
    penalty_winner: Mapped[str | None] = mapped_column(String(3), nullable=True)
    # True si se importó automáticamente desde football-data.org
    auto_loaded: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class FinalPick(Base):
    __tablename__ = "final_picks"

    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    champion: Mapped[str] = mapped_column(String(3), nullable=False)
    runner_up: Mapped[str] = mapped_column(String(3), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    user: Mapped[User] = relationship(back_populates="final_pick")


class OfficialFinal(Base):
    __tablename__ = "official_final"
    __table_args__ = (
        CheckConstraint("id = 1", name="ck_official_final_singleton"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    champion: Mapped[str | None] = mapped_column(String(3), nullable=True)
    runner_up: Mapped[str | None] = mapped_column(String(3), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class KnockoutMatch(Base):
    """Asignación de equipos para un slot de fase eliminatoria (K1..K30).

    Se popula automáticamente desde football-data.org cuando FIFA define
    los cruces, sobreescribiendo la entrada del FIXTURE (que arranca como
    'TBD vs TBD'). El admin puede editar manualmente seteando source='manual'
    y en ese caso el auto-sync no la pisa.
    """
    __tablename__ = "knockout_matches"

    match_id: Mapped[str] = mapped_column(String(10), primary_key=True)
    home_tla: Mapped[str] = mapped_column(String(3), nullable=False)
    away_tla: Mapped[str] = mapped_column(String(3), nullable=False)
    datetime_utc: Mapped[str] = mapped_column(String(40), nullable=False)
    venue: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source: Mapped[str] = mapped_column(
        String(10), nullable=False, default="auto", server_default="auto"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class Comment(Base):
    __tablename__ = "comments"
    __table_args__ = (
        CheckConstraint("char_length(body) BETWEEN 1 AND 500", name="ck_comments_body_len"),
        Index("ix_comments_created_at", "created_at"),
        Index("ix_comments_parent_id", "parent_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    body: Mapped[str] = mapped_column(String(500), nullable=False)
    # NULL = comentario raíz. Si tiene valor, es una respuesta a otro comment.
    parent_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("comments.id", ondelete="CASCADE"),
        nullable=True,
    )
    # Destacado por un admin → se muestra con recuadro verde.
    highlighted: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), nullable=False, server_default=func.now()
    )
    # NULL = nunca editado. Cualquier PATCH lo setea con datetime.utcnow().
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=False), nullable=True, default=None
    )

    user: Mapped[User] = relationship(back_populates="comments")
    likes: Mapped[list["CommentLike"]] = relationship(
        back_populates="comment", cascade="all, delete-orphan", passive_deletes=True
    )


class CommentLike(Base):
    __tablename__ = "comment_likes"
    __table_args__ = (
        Index("ix_comment_likes_comment_id", "comment_id"),
    )

    comment_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("comments.id", ondelete="CASCADE"),
        primary_key=True,
    )
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), nullable=False, server_default=func.now()
    )

    comment: Mapped[Comment] = relationship(back_populates="likes")
    user: Mapped[User] = relationship()
