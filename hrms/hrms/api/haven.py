import frappe
from frappe import _
import json
import requests
import hashlib
import uuid
from datetime import datetime, timedelta

@frappe.whitelist()
def get_weekly_metrics():
    """
    Collect real weekly employee metrics, encrypt them using the Haven public key with JWE,
    and send them to Haven over HTTPS with the X-Service-Token.
    """
    public_key_pem = frappe.conf.get("haven_public_key")
    key_id = frappe.conf.get("haven_key_id", "haven-key-2026-01")
    haven_url = frappe.conf.get("haven_api_url", "http://localhost:8000/api/v1/ingestion/metrics")
    service_token = frappe.conf.get("haven_service_token")

    # Do not use default service token in non-development environments
    if frappe.conf.get("developer_mode") != 1 and service_token == "default_dev_service_token_replace_in_prod":
        frappe.throw(_("Cannot use default dev service token in production."))

    if not service_token:
        frappe.throw(_("HAVEN_SERVICE_TOKEN is not configured."))
    if not public_key_pem:
        frappe.throw(_("HAVEN_PUBLIC_KEY is not configured in site config."))
    if not haven_url:
        frappe.throw(_("HAVEN_API_URL is not configured."))

    try:
        from jwcrypto import jwk, jwe
    except ImportError:
        frappe.throw(_("jwcrypto library is not installed."))

    # Query Active Employees
    employees = frappe.get_all("Employee", filters={"status": "Active"}, fields=[
        "name", "department", "designation", "date_of_joining", "employment_type", "reports_to"
    ])

    today = datetime.today()
    # Ensure standard week start (Monday)
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)

    week_start_date = week_start.date().isoformat()
    week_end_date = week_end.date().isoformat()

    metrics = []

    for emp in employees:
        # Stable SHA-256 employee hash (no raw PII)
        emp_hash = hashlib.sha256(emp.name.encode('utf-8')).hexdigest()

        # Tenure
        tenure_months = 0
        if emp.date_of_joining:
            doj = emp.date_of_joining
            if isinstance(doj, str):
                doj = datetime.strptime(doj, "%Y-%m-%d").date()
            tenure_months = (today.date().year - doj.year) * 12 + today.date().month - doj.month

        # Team Size
        team_size = None
        if emp.reports_to:
            team_size = frappe.db.count("Employee", filters={"reports_to": emp.reports_to, "status": "Active"})

        # Attendance Data
        attendances = frappe.get_all("Attendance", filters={
            "employee": emp.name,
            "attendance_date": ["between", [week_start_date, week_end_date]],
            "docstatus": 1
        }, fields=["attendance_date", "status", "working_hours", "late_entry", "early_exit", "out_time"], order_by="attendance_date asc")

        avg_daily_work_hours = None
        late_entry_count = 0
        early_exit_count = 0
        missing_checkout_count = 0
        weekend_work_days = 0
        leave_days_taken = 0
        total_working_hours = 0
        days_present = 0

        unique_attendance_dates = set()
        worked_dates = set()

        for att in attendances:
            att_date = att.attendance_date
            if isinstance(att_date, str):
                att_date = datetime.strptime(att_date, "%Y-%m-%d").date()

            if att.status in ["Present", "Half Day"]:
                if att_date not in worked_dates:
                    days_present += 1
                    worked_dates.add(att_date)

                    if att.working_hours:
                        total_working_hours += float(att.working_hours)
                    if att.late_entry:
                        late_entry_count += 1
                    if att.early_exit:
                        early_exit_count += 1
                    if not att.out_time:
                        missing_checkout_count += 1

                    if att_date.weekday() >= 5: # Saturday or Sunday
                        weekend_work_days += 1

            if att.status == "On Leave" and att_date not in unique_attendance_dates:
                leave_days_taken += 1

            unique_attendance_dates.add(att_date)

        if days_present > 0:
            avg_daily_work_hours = total_working_hours / days_present

        # Consecutive workdays
        consecutive_work_days = 0
        current_streak = 0
        prev_date = None
        for d in sorted(list(worked_dates)):
            if prev_date and (d - prev_date).days == 1:
                current_streak += 1
            else:
                current_streak = 1
            if current_streak > consecutive_work_days:
                consecutive_work_days = current_streak
            prev_date = d

        # Timesheet Data
        timesheets = frappe.get_all("Timesheet", filters={
            "employee": emp.name,
            "start_date": ["between", [week_start_date, week_end_date]],
            "docstatus": 1
        }, fields=["total_hours"])
        timesheet_hours = sum([float(ts.total_hours or 0) for ts in timesheets]) if timesheets else None

        # Overtime calculation
        overtime_hours = None
        try:
            default_shift = frappe.db.get_value("Employee", emp.name, "default_shift")
            if default_shift:
                shift = frappe.get_doc("Shift Type", default_shift)
                if shift.start_time and shift.end_time:
                    t1 = datetime.strptime(str(shift.start_time), "%H:%M:%S")
                    t2 = datetime.strptime(str(shift.end_time), "%H:%M:%S")
                    daily_scheduled = (t2 - t1).seconds / 3600.0
                    weekly_scheduled = daily_scheduled * 5

                    actual_hours = timesheet_hours if timesheet_hours is not None else total_working_hours
                    if actual_hours is not None:
                        overtime_hours = max(actual_hours - weekly_scheduled, 0.0)
        except Exception:
            pass

        # Unplanned leaves
        notice_period_days = frappe.conf.get("haven_leave_notice_period_days", 3)
        unplanned_leave_count = None
        try:
            leaves = frappe.get_all("Leave Application", filters={
                "employee": emp.name,
                "from_date": ["<=", week_end_date],
                "to_date": [">=", week_start_date],
                "status": "Approved",
                "docstatus": 1
            }, fields=["posting_date", "from_date"])

            if leaves is not None: # Can be empty list
                unplanned_leave_count = 0
                for leave in leaves:
                    posting = leave.posting_date
                    from_d = leave.from_date
                    if isinstance(posting, str):
                        posting = datetime.strptime(posting, "%Y-%m-%d").date()
                    if isinstance(from_d, str):
                        from_d = datetime.strptime(from_d, "%Y-%m-%d").date()

                    if (from_d - posting).days < notice_period_days:
                        unplanned_leave_count += 1
        except Exception:
            unplanned_leave_count = None

        # Payroll issues
        payroll_issue_count = None
        try:
            slips = frappe.get_all("Salary Slip", filters={
                "employee": emp.name,
                "start_date": ["<=", week_end_date],
                "end_date": [">=", week_start_date]
            }, fields=["status"])

            if slips is not None:
                payroll_issue_count = 0
                for slip in slips:
                    if slip.status in ["Rejected", "Cancelled", "Failed"]:
                        payroll_issue_count += 1
        except Exception:
            payroll_issue_count = None

        # Appraisal Data (latest)
        appraisals = frappe.get_all("Appraisal", filters={
            "employee": emp.name,
            "docstatus": 1
        }, fields=["total_score"], order_by="creation desc", limit=1)
        appraisal_rating = float(appraisals[0].total_score) if appraisals and appraisals[0].total_score else None

        # Build metric dictionary
        metric_dict = {
            "employee_hash": emp_hash,
            "week_start_date": week_start_date,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "request_id": str(uuid.uuid4()),

            "department": emp.department,
            "designation": emp.designation,
            "employment_type": emp.employment_type,
            "tenure_months": max(0, tenure_months) if tenure_months else 0,
            "team_size": team_size,

            "avg_daily_work_hours": avg_daily_work_hours,
            "overtime_hours": overtime_hours,

            "late_entry_count": late_entry_count,
            "early_exit_count": early_exit_count,
            "missing_checkout_count": missing_checkout_count,
            "weekend_work_days": weekend_work_days,
            "holiday_work_days": None, # Unavailable standardly
            "consecutive_work_days": consecutive_work_days,
            "night_shift_count": None, # Unavailable standardly
            "shift_change_count": None, # Unavailable standardly

            "leave_days_taken": leave_days_taken,
            "unused_leave_balance": None, # Requires complex leave ledger query
            "unplanned_leave_count": unplanned_leave_count,
            "leave_cancellation_count": None, # Unavailable standardly

            "timesheet_hours": timesheet_hours,
            "timesheet_correction_count": None, # Unavailable standardly

            "payroll_issue_count": payroll_issue_count,

            "appraisal_rating": appraisal_rating,
            "goal_completion_percent": None # Unavailable standardly
        }

        # Data Completeness
        expected_metrics = [
            "department", "designation", "employment_type", "tenure_months", "team_size",
            "avg_daily_work_hours", "overtime_hours", "late_entry_count", "early_exit_count",
            "missing_checkout_count", "weekend_work_days", "holiday_work_days",
            "consecutive_work_days", "night_shift_count", "shift_change_count",
            "leave_days_taken", "unused_leave_balance", "unplanned_leave_count",
            "leave_cancellation_count", "timesheet_hours", "timesheet_correction_count",
            "payroll_issue_count", "appraisal_rating", "goal_completion_percent"
        ]

        missing_fields = [k for k in expected_metrics if metric_dict.get(k) is None]
        data_completeness = (len(expected_metrics) - len(missing_fields)) / len(expected_metrics)
        metric_dict["data_completeness"] = data_completeness

        # Internal log
        if missing_fields:
            frappe.logger().debug(f"Employee {emp_hash} missing metrics: {missing_fields}")

        metrics.append(metric_dict)

    results = []

    try:
        key = jwk.JWK.from_pem(public_key_pem.encode('utf-8'))
    except Exception as e:
        frappe.throw(_("Invalid HAVEN_PUBLIC_KEY: {0}").format(str(e)))

    for metric in metrics:
        payload = json.dumps(metric)
        protected_header = {
            "alg": "RSA-OAEP-256",
            "enc": "A256GCM",
            "kid": key_id
        }

        try:
            jwetoken = jwe.JWE(payload.encode('utf-8'), recipient=key, protected=protected_header)
            enc_compact = jwetoken.serialize(compact=True)

            headers = {
                "X-Service-Token": service_token,
                "Content-Type": "application/json"
            }

            resp = requests.post(haven_url, json={"jwe": enc_compact}, headers=headers, timeout=10)

            if resp.status_code in [200, 201]:
                results.append({"employee": metric["employee_hash"], "status": "success"})
            else:
                results.append({"employee": metric["employee_hash"], "status": "failed", "error": f"HTTP {resp.status_code}: {resp.text}"})
        except requests.exceptions.Timeout:
            results.append({"employee": metric["employee_hash"], "status": "failed", "error": "Request timed out"})
        except requests.exceptions.RequestException as e:
            results.append({"employee": metric["employee_hash"], "status": "failed", "error": f"Request failed: {str(e)}"})
        except Exception as e:
            results.append({"employee": metric["employee_hash"], "status": "failed", "error": f"Encryption/Processing failed: {str(e)}"})

    return results
