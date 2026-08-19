"""initial empty migration

Revision ID: f60ce55d7494
Revises: 
Create Date: 2026-08-19 17:25:15.337097

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'f60ce55d7494'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
