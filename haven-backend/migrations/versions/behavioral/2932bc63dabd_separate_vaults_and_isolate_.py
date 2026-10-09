"""Separate vaults and isolate BurnoutPrediction

Revision ID: 2932bc63dabd
Revises: e4ae969e0060
Create Date: 2026-10-08 21:26:14.216233

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2932bc63dabd'
down_revision: Union[str, None] = 'e4ae969e0060'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    print("Migrating behavioral database: dropping columns from weekly_employee_metrics")
    op.drop_column('weekly_employee_metrics', 'probability_high')
    op.drop_column('weekly_employee_metrics', 'probability_medium')
    op.drop_column('weekly_employee_metrics', 'probability_low')
    op.drop_column('weekly_employee_metrics', 'shap_explanations')
    op.drop_column('weekly_employee_metrics', 'model_version')


def downgrade() -> None:
    op.add_column('weekly_employee_metrics', sa.Column('model_version', sa.VARCHAR(), nullable=True))
    op.add_column('weekly_employee_metrics', sa.Column('shap_explanations', sa.VARCHAR(), nullable=True))
    op.add_column('weekly_employee_metrics', sa.Column('probability_low', sa.FLOAT(), nullable=True))
    op.add_column('weekly_employee_metrics', sa.Column('probability_medium', sa.FLOAT(), nullable=True))
    op.add_column('weekly_employee_metrics', sa.Column('probability_high', sa.FLOAT(), nullable=True))
