"""Initial migration

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
