import logging
from sqlalchemy.orm import Session
from app.database.connection import SessionLocal, BehavioralSessionLocal
from app.database import models
from app.security.password import get_password_hash
import uuid
import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def seed_database():
    from app.database.connection import engine, identity_engine, behavioral_engine
    logger.info("Creating tables...")
    models.Base.metadata.create_all(bind=engine)
    models.Base.metadata.create_all(bind=identity_engine)
    models.Base.metadata.create_all(bind=behavioral_engine)
    
    db: Session = SessionLocal()
    try:
        # Create users
        logger.info("Seeding users...")
        users = [
            models.User(username="hr_admin", password_hash=get_password_hash("admin123"), role="HR_ADMIN", is_active=True),
            models.User(username="manager_bob", password_hash=get_password_hash("manager123"), role="MANAGER", is_active=True),
            models.User(username="employee_alice", password_hash=get_password_hash("employee123"), role="EMPLOYEE", employee_hash="alice_hash_xyz", is_active=True),
            # 10 More Users
            models.User(username="employee_charlie", password_hash=get_password_hash("employee123"), role="EMPLOYEE", employee_hash="charlie_hash_xyz", is_active=True),
            models.User(username="employee_diana", password_hash=get_password_hash("employee123"), role="EMPLOYEE", employee_hash="diana_hash_xyz", is_active=True),
            models.User(username="employee_eve", password_hash=get_password_hash("employee123"), role="EMPLOYEE", employee_hash="eve_hash_xyz", is_active=True),
            models.User(username="employee_frank", password_hash=get_password_hash("employee123"), role="EMPLOYEE", employee_hash="frank_hash_xyz", is_active=True),
            models.User(username="employee_grace", password_hash=get_password_hash("employee123"), role="EMPLOYEE", employee_hash="grace_hash_xyz", is_active=True),
            models.User(username="employee_hank", password_hash=get_password_hash("employee123"), role="EMPLOYEE", employee_hash="hank_hash_xyz", is_active=True),
            models.User(username="employee_ivy", password_hash=get_password_hash("employee123"), role="EMPLOYEE", employee_hash="ivy_hash_xyz", is_active=True),
            models.User(username="employee_jack", password_hash=get_password_hash("employee123"), role="EMPLOYEE", employee_hash="jack_hash_xyz", is_active=True),
            models.User(username="manager_karen", password_hash=get_password_hash("manager123"), role="MANAGER", department="Engineering", is_active=True),
            models.User(username="manager_leo", password_hash=get_password_hash("manager123"), role="MANAGER", department="Sales", is_active=True),
        ]
        
        for user in users:
            existing = db.query(models.User).filter(models.User.username == user.username).first()
            if not existing:
                db.add(user)
        
        db.commit()

        # Create anonymized employee record in behavioral vault
        logger.info("Seeding employee metrics...")
        b_db = BehavioralSessionLocal()
        try:
            today = datetime.date.today()
            week_start = today - datetime.timedelta(days=today.weekday())
            
            base_metric_args = dict(
                week_start_date=week_start,
                department="Engineering",
                designation="Software Engineer",
                employment_type="Full-Time",
                tenure_months=24,
                team_size=5,
                avg_daily_work_hours=9.5,
                overtime_hours=8.0,
                late_entry_count=1,
                early_exit_count=0,
                missing_checkout_count=0,
                weekend_work_days=1,
                holiday_work_days=0,
                consecutive_work_days=6,
                night_shift_count=0,
                shift_change_count=0,
                leave_days_taken=0,
                unused_leave_balance=15.0,
                unplanned_leave_count=0,
                leave_cancellation_count=0,
                timesheet_hours=48.0,
                timesheet_correction_count=1,
                github_commit_count=25,
                after_hours_commit_count=5,
                weekend_commit_count=2,
                pull_request_count=4,
                review_count=8,
                review_response_hours=2.5,
                issue_count=3,
                issue_resolution_hours=24.0,
                grievance_count=0,
                grievance_resolution_days=0.0,
                travel_days=0,
                payroll_issue_count=0,
                burnout_score=0.45,
                burnout_risk="Low",
                schema_version="1.0",
                data_completeness=1.0,
                label_source="seed"
            )

            metrics = [
                models.WeeklyEmployeeMetrics(employee_hash="alice_hash_xyz", **base_metric_args),
                models.WeeklyEmployeeMetrics(employee_hash="charlie_hash_xyz", **{**base_metric_args, "avg_daily_work_hours": 8.0, "overtime_hours": 2.0, "burnout_risk": "Low"}),
                models.WeeklyEmployeeMetrics(employee_hash="diana_hash_xyz", **{**base_metric_args, "avg_daily_work_hours": 12.0, "overtime_hours": 15.0, "burnout_risk": "High"}),
                models.WeeklyEmployeeMetrics(employee_hash="eve_hash_xyz", **{**base_metric_args, "avg_daily_work_hours": 10.0, "overtime_hours": 10.0, "burnout_risk": "Medium"}),
                models.WeeklyEmployeeMetrics(employee_hash="frank_hash_xyz", **{**base_metric_args, "avg_daily_work_hours": 7.5, "overtime_hours": 0.0, "burnout_risk": "Low"}),
                models.WeeklyEmployeeMetrics(employee_hash="grace_hash_xyz", **{**base_metric_args, "avg_daily_work_hours": 11.5, "overtime_hours": 14.0, "burnout_risk": "High"}),
                models.WeeklyEmployeeMetrics(employee_hash="hank_hash_xyz", **{**base_metric_args, "avg_daily_work_hours": 9.0, "overtime_hours": 5.0, "burnout_risk": "Low"}),
                models.WeeklyEmployeeMetrics(employee_hash="ivy_hash_xyz", **{**base_metric_args, "avg_daily_work_hours": 9.5, "overtime_hours": 8.0, "burnout_risk": "Medium"}),
                models.WeeklyEmployeeMetrics(employee_hash="jack_hash_xyz", **{**base_metric_args, "avg_daily_work_hours": 8.5, "overtime_hours": 1.0, "burnout_risk": "Low"}),
            ]
            
            for metric in metrics:
                existing_metric = b_db.query(models.WeeklyEmployeeMetrics).filter(
                    models.WeeklyEmployeeMetrics.employee_hash == metric.employee_hash,
                    models.WeeklyEmployeeMetrics.week_start_date == metric.week_start_date
                ).first()
                if not existing_metric:
                    b_db.add(metric)
            b_db.commit()
        finally:
            b_db.close()

        logger.info("Database seeded successfully!")

    except Exception as e:
        logger.error(f"Error seeding database: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()
