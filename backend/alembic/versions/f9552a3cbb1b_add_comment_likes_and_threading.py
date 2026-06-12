"""add comments.parent_id (threading) and comment_likes table

Revision ID: f9552a3cbb1b
Revises: eab040268ec8
Create Date: 2026-06-08 00:00:00.000000

Migración NO destructiva:
- Agrega `comments.parent_id` nullable + index + FK self-reference con
  ON DELETE CASCADE. Comentarios existentes quedan con parent_id=NULL
  (todos top-level).
- Crea tabla `comment_likes(comment_id, user_id, created_at)` con PK
  compuesta y FK CASCADE.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'f9552a3cbb1b'
down_revision: Union[str, None] = 'eab040268ec8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'comments',
        sa.Column('parent_id', sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        'fk_comments_parent',
        'comments', 'comments',
        ['parent_id'], ['id'],
        ondelete='CASCADE',
    )
    op.create_index('ix_comments_parent_id', 'comments', ['parent_id'], unique=False)

    op.create_table(
        'comment_likes',
        sa.Column('comment_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column(
            'created_at', sa.DateTime(),
            server_default=sa.text('now()'), nullable=False,
        ),
        sa.ForeignKeyConstraint(['comment_id'], ['comments.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('comment_id', 'user_id'),
    )
    op.create_index('ix_comment_likes_comment_id', 'comment_likes', ['comment_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_comment_likes_comment_id', table_name='comment_likes')
    op.drop_table('comment_likes')
    op.drop_index('ix_comments_parent_id', table_name='comments')
    op.drop_constraint('fk_comments_parent', 'comments', type_='foreignkey')
    op.drop_column('comments', 'parent_id')
