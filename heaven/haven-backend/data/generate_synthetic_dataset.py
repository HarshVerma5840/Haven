import random
import uuid
from datetime import date, timedelta
from app.schemas.metrics import WeeklyEmployeeMetricsInput
from app.services.dataset_service import DatasetService

def generate_synthetic_dataset(output_path: str, num_employees: int = 50, num_weeks: int = 12, seed: int = 42):
    """
    Generates a reproducible synthetic dataset using a fixed random seed.
    Produces structurally identical records to the unified schema but strictly labels 
    them as "synthetic".
    """
    random.seed(seed)
    
    departments = ["Engineering", "Product", "Design", "Sales", "HR"]
    designations = ["Junior", "Mid", "Senior", "Lead", "Manager"]
    employment_types = ["Full-Time", "Contractor", "Part-Time"]
    
    start_date = date(2026, 1, 5) # A Monday
    
    # Generate stable employee profiles
    employees = []
    for _ in range(num_employees):
        employees.append({
            "hash": str(uuid.UUID(int=random.getrandbits(128), version=4)),
            "dept": random.choice(departments),
            "desig": random.choice(designations),
            "emp_type": random.choice(employment_types),
            "tenure": round(random.uniform(1.0, 60.0), 1),
            "team_size": random.randint(3, 15)
        })
        
    records = []
    
    for emp in employees:
        for week in range(num_weeks):
            week_date = start_date + timedelta(weeks=week)
            
            # Intentional missing values (10% chance for some optional fields)
            has_timesheet = random.random() > 0.1
            has_github = random.random() > 0.1
            has_appraisal = random.random() > 0.8 # Appraisals are rare
            
            # Base variables for burnout heuristic
            after_hours = random.randint(0, 15) if has_github else 0
            weekend_commits = random.randint(0, 10) if has_github else 0
            overtime = round(random.uniform(0.0, 15.0), 1) if has_timesheet else 0.0
            
            # Burnout score (Synthetic target heuristic - NOT CLINICALLY VALIDATED)
            # Higher after hours, weekends, and overtime increase the score
            base_stress = random.uniform(0.1, 0.4)
            stress_factors = (after_hours * 0.02) + (weekend_commits * 0.03) + (overtime * 0.02)
            
            burnout_score = min(1.0, base_stress + stress_factors)
            
            # Derive risk
            if burnout_score > 0.7:
                burnout_risk = "High"
            elif burnout_score > 0.4:
                burnout_risk = "Medium"
            else:
                burnout_risk = "Low"
                
            # Populate record
            record_dict = {
                "employee_hash": emp["hash"],
                "week_start_date": week_date,
                "department": emp["dept"],
                "designation": emp["desig"],
                "employment_type": emp["emp_type"],
                "tenure_months": emp["tenure"],
                "team_size": emp["team_size"],
                
                "avg_daily_work_hours": round(random.uniform(6.0, 10.0), 1) if has_timesheet else None,
                "overtime_hours": overtime if has_timesheet else None,
                "late_entry_count": random.randint(0, 3),
                "early_exit_count": random.randint(0, 3),
                "missing_checkout_count": random.randint(0, 1),
                "weekend_work_days": random.randint(0, 2),
                "holiday_work_days": random.randint(0, 1),
                "consecutive_work_days": random.randint(5, 12),
                "night_shift_count": random.randint(0, 5),
                "shift_change_count": random.randint(0, 2),
                
                "leave_days_taken": round(random.uniform(0.0, 2.0), 1),
                "unused_leave_balance": round(random.uniform(5.0, 25.0), 1),
                "unplanned_leave_count": random.randint(0, 1),
                "leave_cancellation_count": random.randint(0, 1),
                
                "timesheet_hours": round(random.uniform(30.0, 50.0), 1) if has_timesheet else None,
                "timesheet_correction_count": random.randint(0, 3) if has_timesheet else None,
                "workload_change_percent": round(random.uniform(0.0, 100.0), 1),
                
                "github_commit_count": random.randint(5, 50) if has_github else None,
                "after_hours_commit_count": after_hours if has_github else None,
                "weekend_commit_count": weekend_commits if has_github else None,
                "pull_request_count": random.randint(0, 10) if has_github else None,
                
                "appraisal_rating": round(random.uniform(1.0, 5.0), 1) if has_appraisal else None,
                "goal_completion_percent": round(random.uniform(40.0, 100.0), 1),
                "grievance_count": random.randint(0, 2),
                "grievance_resolution_days": round(random.uniform(1.0, 14.0), 1),
                "travel_days": random.randint(0, 5),
                "payroll_issue_count": random.randint(0, 1),
                
                "burnout_score": round(burnout_score, 2),
                "burnout_risk": burnout_risk,
                "schema_version": "1.0",
                "label_source": "synthetic"
            }
            
            # Handling review counts and response hours properly
            if has_github:
                rev_count = random.randint(0, 15)
                record_dict["review_count"] = rev_count
                record_dict["review_response_hours"] = round(random.uniform(1.0, 48.0), 1) if rev_count > 0 else None
                
                iss_count = random.randint(0, 20)
                record_dict["issue_count"] = iss_count
                record_dict["issue_resolution_hours"] = round(random.uniform(2.0, 72.0), 1) if iss_count > 0 else None
            else:
                record_dict["review_count"] = None
                record_dict["review_response_hours"] = None
                record_dict["issue_count"] = None
                record_dict["issue_resolution_hours"] = None

            # Validate via Pydantic schema
            record = WeeklyEmployeeMetricsInput(**record_dict)
            records.append(record)
            
    service = DatasetService()
    # Calculates data completeness natively
    service.export_records_to_csv(records, output_path)
    return records

if __name__ == "__main__":
    generate_synthetic_dataset("haven-backend/data/synthetic_burnout_dataset.csv")
