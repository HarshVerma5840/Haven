"""Rename probability fields

Revision ID: e4ae969e0060
Revises: a2482c99d090_b
Create Date: 2026-10-08 20:31:02.775839

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e4ae969e0060'
down_revision: Union[str, None] = 'a2482c99d090_b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    print("Migrating behavioral database: renaming probability fields")
    op.alter_column('burnout_predictions', 'probability_low', new_column_name='low_probability')
    op.alter_column('burnout_predictions', 'probability_medium', new_column_name='medium_probability')
    op.alter_column('burnout_predictions', 'probability_high', new_column_name='high_probability')


def downgrade() -> None:
    op.alter_column('burnout_predictions', 'low_probability', new_column_name='probability_low')
    op.alter_column('burnout_predictions', 'medium_probability', new_column_name='probability_medium')
    op.alter_column('burnout_predictions', 'high_probability', new_column_name='probability_high')
