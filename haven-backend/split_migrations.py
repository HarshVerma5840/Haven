import os

base_dir = os.path.dirname(os.path.abspath(__file__))
versions_dir = os.path.join(base_dir, 'migrations', 'versions')

core_code = '''"""Add users table

Revision ID: e70388c8c782
Revises: 
Create Date: 2026-10-08 22:11:39.159524

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e70388c8c782'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    print("Migrating core database: creating users table")
    op.create_table('users',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('username', sa.String(), nullable=False),
    sa.Column('password_hash', sa.String(), nullable=False),
    sa.Column('role', sa.Enum('HR_ADMIN', 'MANAGER', 'EMPLOYEE', name='roleenum'), nullable=False),
    sa.Column('employee_hash', sa.String(), nullable=True),
    sa.Column('department', sa.String(), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)
    op.create_index(op.f('ix_users_username'), 'users', ['username'], unique=True)
    op.create_index(op.f('ix_users_employee_hash'), 'users', ['employee_hash'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_users_employee_hash'), table_name='users')
    op.drop_index(op.f('ix_users_username'), table_name='users')
    op.drop_index(op.f('ix_users_id'), table_name='users')
    op.drop_table('users')
'''

iden_1 = '''"""Add identity mappings

Revision ID: acd6dd4e1b02
Revises: 
Create Date: 2026-10-08 19:11:25.940414

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'acd6dd4e1b02'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    print("Migrating identity database: creating identity_mappings table")
    op.create_table('identity_mappings',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('employee_hash', sa.String(), nullable=False),
    sa.Column('email', sa.String(), nullable=True),
    sa.Column('github_username', sa.String(), nullable=True),
    sa.Column('hrms_employee_id', sa.String(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_identity_mappings_email'), 'identity_mappings', ['email'], unique=True)
    op.create_index(op.f('ix_identity_mappings_employee_hash'), 'identity_mappings', ['employee_hash'], unique=True)
    op.create_index(op.f('ix_identity_mappings_github_username'), 'identity_mappings', ['github_username'], unique=True)
    op.create_index(op.f('ix_identity_mappings_hrms_employee_id'), 'identity_mappings', ['hrms_employee_id'], unique=True)
    op.create_index(op.f('ix_identity_mappings_id'), 'identity_mappings', ['id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_identity_mappings_id'), table_name='identity_mappings')
    op.drop_index(op.f('ix_identity_mappings_hrms_employee_id'), table_name='identity_mappings')
    op.drop_index(op.f('ix_identity_mappings_github_username'), table_name='identity_mappings')
    op.drop_index(op.f('ix_identity_mappings_employee_hash'), table_name='identity_mappings')
    op.drop_index(op.f('ix_identity_mappings_email'), table_name='identity_mappings')
    op.drop_table('identity_mappings')
'''

iden_2 = '''"""Update identity models

Revision ID: a2482c99d090
Revises: acd6dd4e1b02
Create Date: 2026-10-08 19:27:42.200941

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a2482c99d090'
down_revision: Union[str, None] = 'acd6dd4e1b02'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    print("Migrating identity database: updating identity_mappings table")
    op.drop_index(op.f('ix_identity_mappings_email'), table_name='identity_mappings')
    op.drop_index(op.f('ix_identity_mappings_github_username'), table_name='identity_mappings')
    op.drop_index(op.f('ix_identity_mappings_hrms_employee_id'), table_name='identity_mappings')


def downgrade() -> None:
    op.create_index(op.f('ix_identity_mappings_hrms_employee_id'), 'identity_mappings', ['hrms_employee_id'], unique=1)
    op.create_index(op.f('ix_identity_mappings_github_username'), 'identity_mappings', ['github_username'], unique=1)
    op.create_index(op.f('ix_identity_mappings_email'), 'identity_mappings', ['email'], unique=1)
'''

behav_1 = '''"""Initial migration

Revision ID: 9d80c91efef7
Revises: 
Create Date: 2026-10-08 12:38:04.919663

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9d80c91efef7'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    print("Migrating behavioral database: creating weekly_employee_metrics table")
    op.create_table('weekly_employee_metrics',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('employee_hash', sa.String(), nullable=False),
    sa.Column('week_start_date', sa.Date(), nullable=False),
    sa.Column('department', sa.String(), nullable=True),
    sa.Column('designation', sa.String(), nullable=True),
    sa.Column('employment_type', sa.String(), nullable=True),
    sa.Column('tenure_months', sa.Integer(), nullable=True),
    sa.Column('team_size', sa.Integer(), nullable=True),
    sa.Column('avg_daily_work_hours', sa.Float(), nullable=True),
    sa.Column('overtime_hours', sa.Float(), nullable=True),
    sa.Column('late_entry_count', sa.Integer(), nullable=True),
    sa.Column('early_exit_count', sa.Integer(), nullable=True),
    sa.Column('missing_checkout_count', sa.Integer(), nullable=True),
    sa.Column('weekend_work_days', sa.Integer(), nullable=True),
    sa.Column('holiday_work_days', sa.Integer(), nullable=True),
    sa.Column('consecutive_work_days', sa.Integer(), nullable=True),
    sa.Column('night_shift_count', sa.Integer(), nullable=True),
    sa.Column('shift_change_count', sa.Integer(), nullable=True),
    sa.Column('leave_days_taken', sa.Integer(), nullable=True),
    sa.Column('unused_leave_balance', sa.Float(), nullable=True),
    sa.Column('unplanned_leave_count', sa.Integer(), nullable=True),
    sa.Column('leave_cancellation_count', sa.Integer(), nullable=True),
    sa.Column('timesheet_hours', sa.Float(), nullable=True),
    sa.Column('timesheet_correction_count', sa.Integer(), nullable=True),
    sa.Column('workload_change_percent', sa.Float(), nullable=True),
    sa.Column('github_commit_count', sa.Integer(), nullable=True),
    sa.Column('after_hours_commit_count', sa.Integer(), nullable=True),
    sa.Column('weekend_commit_count', sa.Integer(), nullable=True),
    sa.Column('pull_request_count', sa.Integer(), nullable=True),
    sa.Column('review_count', sa.Integer(), nullable=True),
    sa.Column('review_response_hours', sa.Float(), nullable=True),
    sa.Column('issue_count', sa.Integer(), nullable=True),
    sa.Column('issue_resolution_hours', sa.Float(), nullable=True),
    sa.Column('appraisal_rating', sa.Float(), nullable=True),
    sa.Column('goal_completion_percent', sa.Float(), nullable=True),
    sa.Column('grievance_count', sa.Integer(), nullable=True),
    sa.Column('grievance_resolution_days', sa.Float(), nullable=True),
    sa.Column('travel_days', sa.Integer(), nullable=True),
    sa.Column('payroll_issue_count', sa.Integer(), nullable=True),
    sa.Column('burnout_score', sa.Float(), nullable=True),
    sa.Column('burnout_risk', sa.String(), nullable=True),
    sa.Column('schema_version', sa.String(), nullable=False),
    sa.Column('data_completeness', sa.Float(), nullable=True),
    sa.Column('source_timestamp', sa.DateTime(), nullable=True),
    sa.Column('label_source', sa.String(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('employee_hash', 'week_start_date', name='uq_employee_week')
    )
    op.create_index(op.f('ix_weekly_employee_metrics_id'), 'weekly_employee_metrics', ['id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_weekly_employee_metrics_id'), table_name='weekly_employee_metrics')
    op.drop_table('weekly_employee_metrics')
'''

behav_2 = '''"""Add burnout_predictions

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
'''

behav_3 = '''"""Update behavioral models

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
'''

behav_4 = '''"""Rename probability fields

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
'''

behav_5 = '''"""Separate vaults and isolate BurnoutPrediction

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
'''

with open(os.path.join(versions_dir, 'core', 'e70388c8c782_add_users_table.py'), 'w') as f: f.write(core_code)
with open(os.path.join(versions_dir, 'identity', 'acd6dd4e1b02_add_identity_mappings.py'), 'w') as f: f.write(iden_1)
with open(os.path.join(versions_dir, 'identity', 'a2482c99d090_update_identity_models.py'), 'w') as f: f.write(iden_2)
with open(os.path.join(versions_dir, 'behavioral', '9d80c91efef7_initial_migration.py'), 'w') as f: f.write(behav_1)
with open(os.path.join(versions_dir, 'behavioral', 'acd6dd4e1b02_add_burnout_predictions.py'), 'w') as f: f.write(behav_2)
with open(os.path.join(versions_dir, 'behavioral', 'a2482c99d090_update_behavioral_models.py'), 'w') as f: f.write(behav_3)
with open(os.path.join(versions_dir, 'behavioral', 'e4ae969e0060_rename_probability_fields_in_.py'), 'w') as f: f.write(behav_4)
with open(os.path.join(versions_dir, 'behavioral', '2932bc63dabd_separate_vaults_and_isolate_.py'), 'w') as f: f.write(behav_5)
