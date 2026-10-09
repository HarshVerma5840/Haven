from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import Optional, List, Dict
import math

from app.database.models import User, RoleEnum, WeeklyEmployeeMetrics, BurnoutPrediction
from app.dependencies import get_behavioral_db
from app.security.dependencies import require_manager_or_hr_admin, require_employee_or_above
from app.schemas.employee_directory import EmployeeDirectoryItem, EmployeeDirectoryResponse

router = APIRouter(prefix="/api/v1/employees", tags=["employees"])


@router.get("/directory", response_model=EmployeeDirectoryResponse)
def get_employee_directory(
    search: Optional[str] = Query(None, description="Search by employee hash, department, or designation"),
    department: Optional[str] = Query(None, description="Filter by department"),
    risk: Optional[str] = Query(None, description="Filter by burnout risk (High, Medium, Low)"),
    sort_by: Optional[str] = Query("risk_desc", description="Sort order"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_behavioral_db),
    current_user: User = Depends(require_manager_or_hr_admin)
):
    """
    HR-only directory of pseudonymized behavioral workforce records.
    Never exposes identity-vault fields (emails, HRMS IDs, passwords).
    """
    # Manager role restriction to own department
    allowed_department = department
    if current_user.role == RoleEnum.MANAGER and current_user.department:
        allowed_department = current_user.department

    # Query all metrics ordered by week_start_date descending
    metrics_query = db.query(WeeklyEmployeeMetrics).order_by(desc(WeeklyEmployeeMetrics.week_start_date))
    if allowed_department:
        metrics_query = metrics_query.filter(WeeklyEmployeeMetrics.department == allowed_department)
    all_metrics = metrics_query.all()

    # Query all predictions ordered by week_start_date descending
    preds_query = db.query(BurnoutPrediction).order_by(desc(BurnoutPrediction.week_start_date))
    all_preds = preds_query.all()

    # Aggregate latest record per employee_hash
    latest_metrics: Dict[str, WeeklyEmployeeMetrics] = {}
    for m in all_metrics:
        if m.employee_hash not in latest_metrics:
            latest_metrics[m.employee_hash] = m

    latest_preds: Dict[str, BurnoutPrediction] = {}
    for p in all_preds:
        if p.employee_hash not in latest_preds:
            latest_preds[p.employee_hash] = p

    # Collect all unique employee hashes from both behavioral tables
    all_hashes = set(latest_metrics.keys()).union(set(latest_preds.keys()))

    items: List[EmployeeDirectoryItem] = []
    for emp_hash in all_hashes:
        m = latest_metrics.get(emp_hash)
        p = latest_preds.get(emp_hash)

        # Department filtering for prediction-only records
        dept = m.department if m else None
        if allowed_department and dept and dept != allowed_department:
            continue

        designation = m.designation if m else None
        current_risk = p.predicted_risk if p else (m.burnout_risk if m and m.burnout_risk else "Low")
        pred_date = p.week_start_date if p else (m.week_start_date if m else None)
        model_ver = p.model_version if p else "v1.2.0-prod"
        completeness = float(m.data_completeness) if m and m.data_completeness is not None else 100.0

        items.append(EmployeeDirectoryItem(
            employee_hash=emp_hash,
            department=dept,
            designation=designation,
            current_burnout_risk=current_risk,
            prediction_date=pred_date,
            model_version=model_ver,
            data_completeness=completeness
        ))

    # Search filter
    if search:
        q = search.lower().strip()
        items = [
            it for it in items
            if q in it.employee_hash.lower()
            or (it.department and q in it.department.lower())
            or (it.designation and q in it.designation.lower())
        ]

    # Department filter (if not already handled)
    if department:
        items = [it for it in items if it.department == department]

    # Risk filter
    if risk:
        items = [it for it in items if it.current_burnout_risk.lower() == risk.lower()]

    # Sorting
    risk_rank = {"high": 3, "medium": 2, "low": 1}
    if sort_by == "risk_desc":
        items.sort(key=lambda it: (risk_rank.get(it.current_burnout_risk.lower(), 0), it.prediction_date or ""), reverse=True)
    elif sort_by == "risk_asc":
        items.sort(key=lambda it: (risk_rank.get(it.current_burnout_risk.lower(), 0), it.prediction_date or ""))
    elif sort_by == "date_desc":
        items.sort(key=lambda it: it.prediction_date or "", reverse=True)
    elif sort_by == "date_asc":
        items.sort(key=lambda it: it.prediction_date or "")
    elif sort_by == "completeness_desc":
        items.sort(key=lambda it: it.data_completeness, reverse=True)
    elif sort_by == "completeness_asc":
        items.sort(key=lambda it: it.data_completeness)

    total = len(items)
    pages = math.ceil(total / page_size) if total > 0 else 1

    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    paginated_items = items[start_idx:end_idx]

    return EmployeeDirectoryResponse(
        items=paginated_items,
        total=total,
        page=page,
        page_size=page_size,
        pages=pages
    )


@router.get("/{employee_hash}")
def get_employee_data(
    employee_hash: str,
    db: Session = Depends(get_behavioral_db),
    current_user: User = Depends(require_employee_or_above)
):
    """Retrieve behavioral employee profile (anonymized metrics only)."""
    # Enforce record ownership
    if current_user.role == RoleEnum.EMPLOYEE:
        if current_user.employee_hash != employee_hash:
            raise HTTPException(status_code=403, detail="Employees can only access their own records.")

    metrics = db.query(WeeklyEmployeeMetrics).filter(
        WeeklyEmployeeMetrics.employee_hash == employee_hash
    ).order_by(desc(WeeklyEmployeeMetrics.week_start_date)).first()

    if current_user.role == RoleEnum.MANAGER and current_user.department:
        if metrics and metrics.department != current_user.department:
            raise HTTPException(status_code=403, detail="Managers can only access records for their department.")

    prediction = db.query(BurnoutPrediction).filter(
        BurnoutPrediction.employee_hash == employee_hash
    ).order_by(desc(BurnoutPrediction.week_start_date)).first()

    return {
        "employee_hash": employee_hash,
        "department": metrics.department if metrics else None,
        "designation": metrics.designation if metrics else None,
        "avg_daily_work_hours": metrics.avg_daily_work_hours if metrics else None,
        "overtime_hours": metrics.overtime_hours if metrics else None,
        "leave_days_taken": metrics.leave_days_taken if metrics else None,
        "late_entry_count": metrics.late_entry_count if metrics else None,
        "weekly_timesheet_hours": metrics.timesheet_hours if metrics else None,
        "weekend_work_days": metrics.weekend_work_days if metrics else None,
        "data_completeness": float(metrics.data_completeness) if metrics and metrics.data_completeness is not None else None,
        "current_burnout_risk": prediction.predicted_risk if prediction else (metrics.burnout_risk if metrics else None),
        "prediction_date": prediction.week_start_date if prediction else (metrics.week_start_date if metrics else None),
        "model_version": prediction.model_version if prediction else None,
        "has_data": metrics is not None or prediction is not None,
    }
