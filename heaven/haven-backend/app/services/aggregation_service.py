import datetime
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.database.models import WeeklyEmployeeMetrics
from app.services.github_metrics import GitHubMetricsExtractor
import structlog

logger = structlog.get_logger(__name__)

class AggregationError(Exception):
    pass

class AggregationService:
    def __init__(self, db: Session, github_extractor: GitHubMetricsExtractor):
        self.db = db
        self.github_extractor = github_extractor

    async def aggregate_github_metrics(
        self,
        employee_hash: str,
        github_username: str,
        week_start_date: datetime.date,
        week_end_date: datetime.date
    ) -> WeeklyEmployeeMetrics:
        """
        Extracts metrics from GitHub for a specific user and timeframe,
        and upserts the results into the database.
        """
        if not employee_hash or not github_username:
            raise ValueError("employee_hash and github_username are required")
        if not week_start_date or not week_end_date:
            raise ValueError("week_start_date and week_end_date are required")
            
        logger.info("Extracting GitHub metrics", employee_hash=employee_hash, week_start=str(week_start_date))
        try:
            gh_metrics = await self.github_extractor.extract_weekly_metrics(
                username=github_username,
                start_date=week_start_date,
                end_date=week_end_date
            )
        except Exception as e:
            logger.error("GitHub metrics extraction failed", error=str(e))
            self.db.rollback()
            raise AggregationError(f"GitHub extraction failed: {str(e)}") from e

        try:
            # Idempotency key: (employee_hash, week_start_date)
            stmt = select(WeeklyEmployeeMetrics).where(
                WeeklyEmployeeMetrics.employee_hash == employee_hash,
                WeeklyEmployeeMetrics.week_start_date == week_start_date
            )
            record = self.db.execute(stmt).scalars().first()

            now = datetime.datetime.now(datetime.timezone.utc)

            if not record:
                # First insert
                record = WeeklyEmployeeMetrics(
                    employee_hash=employee_hash,
                    week_start_date=week_start_date
                )
                record.label_source = "pending"
                self.db.add(record)

            # Map GitHub metrics to DB model
            record.github_commit_count = gh_metrics.github_commit_count
            record.after_hours_commit_count = gh_metrics.after_hours_commit_count
            record.weekend_commit_count = gh_metrics.weekend_commit_count
            record.pull_request_count = gh_metrics.pull_request_count
            record.review_count = gh_metrics.review_count
            record.review_response_hours = gh_metrics.review_response_hours
            record.issue_count = gh_metrics.issue_count
            record.issue_resolution_hours = gh_metrics.issue_resolution_hours

            # HRMS fields remain untouched (NULL)
            
            # Required Metadata
            record.schema_version = "1.0"
            record.source_timestamp = now
            # Without HRMS data, dataset is structurally incomplete
            record.data_completeness = 0.5 

            self.db.commit()
            
            # Refresh to get DB-generated fields like IDs
            self.db.refresh(record)
            return record

        except Exception as e:
            self.db.rollback()
            logger.error("Database aggregation failed", error=str(e))
            raise
