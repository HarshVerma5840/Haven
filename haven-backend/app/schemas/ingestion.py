from pydantic import BaseModel, Field
import datetime
from typing import Optional

class EncryptedPayload(BaseModel):
    jwe: str = Field(..., description="JWE compact serialized string")

class HRMSMetricsPayload(BaseModel):
    employee_hash: str = Field(..., description="Anonymized hash of the employee identity")
    week_start_date: datetime.date = Field(..., description="Start date of the week for these metrics")

    timestamp: Optional[datetime.datetime] = Field(None, description="ISO UTC timestamp of the payload generation")
    request_id: Optional[str] = Field(None, description="Unique identifier for replay protection")

    department: Optional[str] = None
    designation: Optional[str] = None
    employment_type: Optional[str] = None
    tenure_months: Optional[int] = Field(None, ge=0)
    team_size: Optional[int] = Field(None, ge=0)

    avg_daily_work_hours: Optional[float] = Field(None, ge=0)
    overtime_hours: Optional[float] = Field(None, ge=0)

    late_entry_count: Optional[int] = Field(None, ge=0)
    early_exit_count: Optional[int] = Field(None, ge=0)
    missing_checkout_count: Optional[int] = Field(None, ge=0)
    weekend_work_days: Optional[int] = Field(None, ge=0, le=2)
    holiday_work_days: Optional[int] = Field(None, ge=0)
    consecutive_work_days: Optional[int] = Field(None, ge=0)
    night_shift_count: Optional[int] = Field(None, ge=0)
    shift_change_count: Optional[int] = Field(None, ge=0)

    leave_days_taken: Optional[int] = Field(None, ge=0)
    unused_leave_balance: Optional[float] = Field(None, ge=0)
    unplanned_leave_count: Optional[int] = Field(None, ge=0)
    leave_cancellation_count: Optional[int] = Field(None, ge=0)

    timesheet_hours: Optional[float] = Field(None, ge=0)
    timesheet_correction_count: Optional[int] = Field(None, ge=0)
    workload_change_percent: Optional[float] = None

    github_commit_count: Optional[int] = Field(None, ge=0)
    after_hours_commit_count: Optional[int] = Field(None, ge=0)
    weekend_commit_count: Optional[int] = Field(None, ge=0)
    pull_request_count: Optional[int] = Field(None, ge=0)
    review_count: Optional[int] = Field(None, ge=0)
    review_response_hours: Optional[float] = Field(None, ge=0)
    issue_count: Optional[int] = Field(None, ge=0)
    issue_resolution_hours: Optional[float] = Field(None, ge=0)

    appraisal_rating: Optional[float] = Field(None, ge=1.0, le=5.0)
    goal_completion_percent: Optional[float] = Field(None, ge=0, le=100)

    grievance_count: Optional[int] = Field(None, ge=0)
    grievance_resolution_days: Optional[float] = Field(None, ge=0)
    travel_days: Optional[int] = Field(None, ge=0)
    payroll_issue_count: Optional[int] = Field(None, ge=0)

    data_completeness: Optional[float] = Field(None, ge=0, le=1)

    class Config:
        json_schema_extra = {
            "example": {
                "employee_hash": "alice_hash_xyz",
                "week_start_date": "2026-10-05",
                "department": "Engineering",
                "avg_daily_work_hours": 9.5,
                "overtime_hours": 8.0,
                "leave_days_taken": 0,
                "appraisal_rating": 4.5
            }
        }
