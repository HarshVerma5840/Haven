from datetime import date
from app.database.connection import engine, behavioral_engine, IdentitySessionLocal
from app.database.base import Base
import app.database.models as models
from app.security.password import get_password_hash
from app.dependencies import get_db, get_behavioral_db

def seed():
    # Ensure tables exist
    Base.metadata.create_all(bind=engine)
    Base.metadata.create_all(bind=behavioral_engine)

    core_db = next(get_db())
    behav_db = next(get_behavioral_db())

    # 1. Seed HR Admin & Manager Users
    if not core_db.query(models.User).filter(models.User.username == "admin").first():
        core_db.add(models.User(
            username="admin",
            password_hash=get_password_hash("admin123"),
            role=models.RoleEnum.HR_ADMIN,
            is_active=True
        ))
        print("Created admin / admin123 (HR_ADMIN)")

    if not core_db.query(models.User).filter(models.User.username == "hr_manager").first():
        core_db.add(models.User(
            username="hr_manager",
            password_hash=get_password_hash("manager123"),
            role=models.RoleEnum.MANAGER,
            department="Engineering",
            is_active=True
        ))
        print("Created hr_manager / manager123 (MANAGER)")

    core_db.commit()

    # 2. Seed Sample Employee Metrics & Predictions if empty
    if behav_db.query(models.WeeklyEmployeeMetrics).count() == 0:
        sample_employees = [
            ("emp_a1b2c3d4e5", "Engineering", "Senior Backend Engineer", "High", 9.8, 14.5, 3, 2, 48.0, 96.0, 0.85, 0.12, 0.03),
            ("emp_f6g7h8i9j0", "Engineering", "Frontend Tech Lead", "Medium", 8.6, 6.0, 1, 0, 42.5, 94.0, 0.45, 0.42, 0.13),
            ("emp_k1l2m3n4o5", "Engineering", "DevOps Engineer", "Low", 7.8, 1.5, 0, 0, 39.0, 98.0, 0.08, 0.22, 0.70),
            ("emp_p6q7r8s9t0", "Sales", "Enterprise Account Exec", "High", 9.2, 11.0, 2, 1, 46.0, 92.0, 0.78, 0.18, 0.04),
            ("emp_u1v2w3x4y5", "Sales", "Sales Development Rep", "Low", 7.5, 0.0, 0, 0, 38.5, 95.0, 0.05, 0.15, 0.80),
            ("emp_z6a7b8c9d0", "HR", "People Operations Lead", "Medium", 8.4, 5.5, 1, 0, 41.0, 97.0, 0.38, 0.48, 0.14),
            ("emp_e1f2g3h4i5", "Finance", "Senior Financial Analyst", "Low", 7.9, 2.0, 0, 0, 40.0, 99.0, 0.10, 0.20, 0.70),
            ("emp_j6k7l8m9n0", "Operations", "Scrum Master & PM", "Medium", 8.2, 4.0, 1, 1, 40.5, 93.0, 0.42, 0.44, 0.14),
        ]

        today = date(2026, 10, 5)

        for emp_hash, dept, desig, risk, daily_hrs, ot, late, wknd, ts_hrs, comp, p_high, p_med, p_low in sample_employees:
            behav_db.add(models.WeeklyEmployeeMetrics(
                employee_hash=emp_hash,
                week_start_date=today,
                department=dept,
                designation=desig,
                avg_daily_work_hours=daily_hrs,
                overtime_hours=ot,
                late_entry_count=late,
                weekend_work_days=wknd,
                timesheet_hours=ts_hrs,
                leave_days_taken=1 if risk != "Low" else 0,
                burnout_risk=risk,
                data_completeness=comp,
                schema_version="1.0",
                label_source="hrms"
            ))

            behav_db.add(models.BurnoutPrediction(
                employee_hash=emp_hash,
                week_start_date=today,
                predicted_risk=risk,
                low_probability=p_low,
                medium_probability=p_med,
                high_probability=p_high,
                model_type="RandomForestClassifier",
                model_version="rf-dev-1.1",
                shap_explanations='{"overtime_hours": 0.384, "weekend_work_days": 0.212, "late_entry_count": 0.145}' if risk == "High" else '{"workload_stability": -0.22, "leave_balance": -0.15}'
            ))

        behav_db.commit()
        print("Seeded 8 sample behavioral employee metrics and predictions.")

if __name__ == "__main__":
    seed()
