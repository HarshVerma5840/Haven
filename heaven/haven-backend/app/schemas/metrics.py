from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import date, datetime

class WeeklyEmployeeMetricsInput(BaseModel):
    """
    Source-independent contract for weekly employee metrics.
    """
    employee_hash: str
    week_start_date: date
    
    # HRMS - Demographics & Tenure
    department: Optional[str] = None
    designation: Optional[str] = None
    employment_type: Optional[str] = None
    tenure_months: Optional[float] = Field(None, ge=0)
    team_size: Optional[int] = Field(None, ge=0)
    
    # HRMS - Hours & Attendance
    avg_daily_work_hours: Optional[float] = Field(None, ge=0)
    overtime_hours: Optional[float] = Field(None, ge=0)
    late_entry_count: Optional[int] = Field(None, ge=0)
    early_exit_count: Optional[int] = Field(None, ge=0)
    missing_checkout_count: Optional[int] = Field(None, ge=0)
    weekend_work_days: Optional[int] = Field(None, ge=0)
    holiday_work_days: Optional[int] = Field(None, ge=0)
    consecutive_work_days: Optional[int] = Field(None, ge=0)
    night_shift_count: Optional[int] = Field(None, ge=0)
    shift_change_count: Optional[int] = Field(None, ge=0)
    
    # HRMS - Leave
    leave_days_taken: Optional[float] = Field(None, ge=0)
    unused_leave_balance: Optional[float] = None # can theoretically be negative in some companies
    unplanned_leave_count: Optional[int] = Field(None, ge=0)
    leave_cancellation_count: Optional[int] = Field(None, ge=0)
    
    # HRMS - Timesheet & Workload
    timesheet_hours: Optional[float] = Field(None, ge=0)
    timesheet_correction_count: Optional[int] = Field(None, ge=0)
    workload_change_percent: Optional[float] = Field(None, ge=0, le=100)
    
    # GitHub
    github_commit_count: Optional[int] = Field(None, ge=0)
    after_hours_commit_count: Optional[int] = Field(None, ge=0)
    weekend_commit_count: Optional[int] = Field(None, ge=0)
    pull_request_count: Optional[int] = Field(None, ge=0)
    review_count: Optional[int] = Field(None, ge=0)
    review_response_hours: Optional[float] = Field(None, ge=0)
    issue_count: Optional[int] = Field(None, ge=0)
    issue_resolution_hours: Optional[float] = Field(None, ge=0)
    
    # HRMS - Performance & Grievances
    appraisal_rating: Optional[float] = Field(None, ge=1, le=5)
    goal_completion_percent: Optional[float] = Field(None, ge=0, le=100)
    grievance_count: Optional[int] = Field(None, ge=0)
    grievance_resolution_days: Optional[float] = Field(None, ge=0)
    travel_days: Optional[int] = Field(None, ge=0)
    payroll_issue_count: Optional[int] = Field(None, ge=0)
    
    # ML / Target
    burnout_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    burnout_risk: Optional[Literal["Low", "Medium", "High"]] = None
    
    # Metadata
    schema_version: str = "1.0"
    data_completeness: Optional[float] = Field(None, ge=0.0, le=1.0)
    source_timestamp: Optional[datetime] = None
    label_source: str = "pending"
