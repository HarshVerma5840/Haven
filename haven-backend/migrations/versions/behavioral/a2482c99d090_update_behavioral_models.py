"""Update behavioral models

Revision ID: a2482c99d090_b
Revises: acd6dd4e1b02_b
Create Date: 2026-10-08 19:27:42.200941

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a2482c99d090_b'
down_revision: Union[str, None] = 'acd6dd4e1b02_b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    print("Migrating behavioral database: adding probability cols")
    op.add_column('weekly_employee_metrics', sa.Column('probability_low', sa.Float(), nullable=True))
    op.add_column('weekly_employee_metrics', sa.Column('probability_medium', sa.Float(), nullable=True))
    op.add_column('weekly_employee_metrics', sa.Column('probability_high', sa.Float(), nullable=True))
    op.add_column('weekly_employee_metrics', sa.Column('shap_explanations', sa.String(), nullable=True))
    op.add_column('weekly_employee_metrics', sa.Column('model_version', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('weekly_employee_metrics', 'model_version')
    op.drop_column('weekly_employee_metrics', 'shap_explanations')
    op.drop_column('weekly_employee_metrics', 'probability_high')
    op.drop_column('weekly_employee_metrics', 'probability_medium')
    op.drop_column('weekly_employee_metrics', 'probability_low')
