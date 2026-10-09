"""Add burnout_predictions

Revision ID: acd6dd4e1b02_b
Revises: 9d80c91efef7
Create Date: 2026-10-08 19:11:25.940414

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'acd6dd4e1b02_b'
down_revision: Union[str, None] = '9d80c91efef7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    print("Migrating behavioral database: creating burnout_predictions table")
    op.create_table('burnout_predictions',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('employee_hash', sa.String(), nullable=False),
    sa.Column('week_start_date', sa.Date(), nullable=False),
    sa.Column('predicted_risk', sa.String(), nullable=False),
    sa.Column('probability_low', sa.Float(), nullable=False),
    sa.Column('probability_medium', sa.Float(), nullable=False),
    sa.Column('probability_high', sa.Float(), nullable=False),
    sa.Column('shap_explanations', sa.String(), nullable=True),
    sa.Column('model_type', sa.String(), nullable=False),
    sa.Column('model_version', sa.String(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('employee_hash', 'week_start_date', 'model_version', name='uq_prediction_week_version')
    )
    op.create_index(op.f('ix_burnout_predictions_employee_hash'), 'burnout_predictions', ['employee_hash'], unique=False)
    op.create_index(op.f('ix_burnout_predictions_id'), 'burnout_predictions', ['id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_burnout_predictions_id'), table_name='burnout_predictions')
    op.drop_index(op.f('ix_burnout_predictions_employee_hash'), table_name='burnout_predictions')
    op.drop_table('burnout_predictions')
