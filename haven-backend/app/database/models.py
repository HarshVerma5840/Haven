from sqlalchemy import Column, String, Date, Integer, Float, CheckConstraint, UniqueConstraint, DateTime, func
from .base import Base

class WeeklyEmployeeMetrics(Base):
    __tablename__ = 'weekly_employee_metrics'

    id = Column(Integer, primary_key=True, index=True)
    employee_hash = Column(String, nullable=False)
    week_start_date = Column(Date, nullable=False)
    
    department = Column(String)
    designation = Column(String)
    employment_type = Column(String)
    tenure_months = Column(Integer)
    team_size = Column(Integer)
    
    avg_daily_work_hours = Column(Float)
    overtime_hours = Column(Float)
    
    late_entry_count = Column(Integer)
    early_exit_count = Column(Integer)
    missing_checkout_count = Column(Integer)
    weekend_work_days = Column(Integer)
    holiday_work_days = Column(Integer)
    consecutive_work_days = Column(Integer)
    night_shift_count = Column(Integer)
    shift_change_count = Column(Integer)
    
    leave_days_taken = Column(Integer)
    unused_leave_balance = Column(Float)
    unplanned_leave_count = Column(Integer)
    leave_cancellation_count = Column(Integer)
    
    timesheet_hours = Column(Float)
    timesheet_correction_count = Column(Integer)
    workload_change_percent = Column(Float)
    
    github_commit_count = Column(Integer)
    after_hours_commit_count = Column(Integer)
    weekend_commit_count = Column(Integer)
    pull_request_count = Column(Integer)
    review_count = Column(Integer)
    review_response_hours = Column(Float)
    issue_count = Column(Integer)
    issue_resolution_hours = Column(Float)
    
    appraisal_rating = Column(Float)
    goal_completion_percent = Column(Float)
    
    grievance_count = Column(Integer)
    grievance_resolution_days = Column(Float)
    travel_days = Column(Integer)
    payroll_issue_count = Column(Integer)
    
    burnout_score = Column(Float)
    burnout_risk = Column(String)
    
    schema_version = Column(String, nullable=False)
    data_completeness = Column(Float)
    source_timestamp = Column(DateTime)
    label_source = Column(String, nullable=False)
    
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint('employee_hash', 'week_start_date', name='uq_employee_week'),
        CheckConstraint('burnout_score >= 0.0 AND burnout_score <= 1.0', name='chk_burnout_score'),
        CheckConstraint('appraisal_rating >= 1.0 AND appraisal_rating <= 5.0', name='chk_appraisal_rating'),
        CheckConstraint('team_size >= 0', name='chk_team_size'),
        CheckConstraint('tenure_months >= 0', name='chk_tenure_months'),
        CheckConstraint('avg_daily_work_hours >= 0', name='chk_avg_daily_work_hours'),
        CheckConstraint('overtime_hours >= 0', name='chk_overtime_hours'),
        CheckConstraint('late_entry_count >= 0', name='chk_late_entry_count'),
        CheckConstraint('early_exit_count >= 0', name='chk_early_exit_count'),
        CheckConstraint('missing_checkout_count >= 0', name='chk_missing_checkout_count'),
        CheckConstraint('weekend_work_days >= 0', name='chk_weekend_work_days'),
        CheckConstraint('holiday_work_days >= 0', name='chk_holiday_work_days'),
        CheckConstraint('consecutive_work_days >= 0', name='chk_consecutive_work_days'),
        CheckConstraint('night_shift_count >= 0', name='chk_night_shift_count'),
        CheckConstraint('shift_change_count >= 0', name='chk_shift_change_count'),
        CheckConstraint('leave_days_taken >= 0', name='chk_leave_days_taken'),
        CheckConstraint('unplanned_leave_count >= 0', name='chk_unplanned_leave_count'),
        CheckConstraint('leave_cancellation_count >= 0', name='chk_leave_cancellation_count'),
        CheckConstraint('timesheet_hours >= 0', name='chk_timesheet_hours'),
        CheckConstraint('timesheet_correction_count >= 0', name='chk_timesheet_correction_count'),
        CheckConstraint('github_commit_count >= 0', name='chk_github_commit_count'),
        CheckConstraint('after_hours_commit_count >= 0', name='chk_after_hours_commit_count'),
        CheckConstraint('weekend_commit_count >= 0', name='chk_weekend_commit_count'),
        CheckConstraint('pull_request_count >= 0', name='chk_pull_request_count'),
        CheckConstraint('review_count >= 0', name='chk_review_count'),
        CheckConstraint('review_response_hours >= 0', name='chk_review_response_hours'),
        CheckConstraint('issue_count >= 0', name='chk_issue_count'),
        CheckConstraint('issue_resolution_hours >= 0', name='chk_issue_resolution_hours'),
        CheckConstraint('grievance_count >= 0', name='chk_grievance_count'),
        CheckConstraint('grievance_resolution_days >= 0', name='chk_grievance_resolution_days'),
        CheckConstraint('travel_days >= 0', name='chk_travel_days'),
        CheckConstraint('payroll_issue_count >= 0', name='chk_payroll_issue_count'),
    )
