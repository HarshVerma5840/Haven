import argparse
import asyncio
import datetime
import sys
from typing import Optional, Dict, Any
import structlog

from app.config import get_settings
from app.database.connection import SessionLocal, IdentitySessionLocal, BehavioralSessionLocal
from app.services.github_client import GitHubClient
from app.services.github_metrics import GitHubMetricsExtractor
from app.services.aggregation_service import AggregationService, AggregationError
from app.database.models import IdentityMapping
from app.security.encryption import decrypt_value

logger = structlog.get_logger(__name__)

async def run_aggregation(
    employee_hash: str,
    github_username: str,
    week_start_date: datetime.date,
    week_end: datetime.date,
    db: Optional[Any] = None,
    client: Optional[GitHubClient] = None,
):
    settings = get_settings()
    
    # Initialize dependencies
    owns_client = False
    if client is None:
        client = GitHubClient()
        owns_client = True
    extractor = GitHubMetricsExtractor(client)
    
    owns_db = False
    if db is None:
        db = BehavioralSessionLocal()
        owns_db = True
    
    try:
        service = AggregationService(db, extractor)
        logger.info(
            "Starting manual GitHub aggregation", 
            employee_hash=employee_hash, 
            week_start_date=str(week_start_date), 
            week_end=str(week_end)
        )
        
        record = await service.aggregate_github_metrics(
            employee_hash=employee_hash,
            github_username=github_username,
            week_start_date=week_start_date,
            week_end_date=week_end
        )
        
        logger.info(
            "Aggregation completed successfully",
            employee_hash=employee_hash,
            record_id=record.id,
            commits=record.github_commit_count,
            prs=record.pull_request_count,
            issues=record.issue_count
        )
        return record
        
    except AggregationError as e:
        logger.error("Aggregation failed due to GitHub API error", error=str(e))
        raise
    except Exception as e:
        logger.error("Aggregation failed due to internal error", error=str(e))
        raise
    finally:
        if owns_db:
            db.close()
        if owns_client:
            await client.close()

async def run_all_employees_aggregation(
    week_start_date: datetime.date,
    week_end: Optional[datetime.date] = None,
    identity_db: Optional[Any] = None,
    behavioral_db: Optional[Any] = None,
    client: Optional[GitHubClient] = None,
) -> Dict[str, Any]:
    """
    Executes weekly GitHub aggregation for all mapped employees in the Identity Vault.
    Pulls the encrypted custom_github_username from HRMS identity mapping,
    aggregates activity, and writes weekly metrics to the behavioral vault.
    Handles missing usernames, inaccessible repos, rate limits, and API failures gracefully.
    """
    if week_end is None:
        week_end = week_start_date + datetime.timedelta(days=6)

    owns_client = False
    if client is None:
        client = GitHubClient()
        owns_client = True
    extractor = GitHubMetricsExtractor(client)

    owns_identity_db = False
    if identity_db is None:
        identity_db = IdentitySessionLocal()
        owns_identity_db = True

    owns_behavioral_db = False
    if behavioral_db is None:
        behavioral_db = BehavioralSessionLocal()
        owns_behavioral_db = True

    try:
        mappings = identity_db.query(IdentityMapping).all()
        logger.info(
            "Starting batch GitHub aggregation across employees",
            total_mappings=len(mappings),
            week_start=str(week_start_date),
            week_end=str(week_end)
        )

        service = AggregationService(behavioral_db, extractor)
        processed = 0
        skipped_no_user = 0
        failed = 0

        for m in mappings:
            emp_hash = m.employee_hash
            raw_gh = None
            if m.github_username:
                try:
                    raw_gh = decrypt_value(m.github_username)
                except Exception as dec_err:
                    logger.warning("Failed to decrypt github username for employee", employee_hash=emp_hash, error=str(dec_err))

            if not raw_gh or not str(raw_gh).strip():
                logger.info("Employee has no custom_github_username mapped; skipping GitHub extraction", employee_hash=emp_hash)
                skipped_no_user += 1
                continue

            try:
                await service.aggregate_github_metrics(
                    employee_hash=emp_hash,
                    github_username=str(raw_gh).strip(),
                    week_start_date=week_start_date,
                    week_end_date=week_end
                )
                processed += 1
            except Exception as e:
                failed += 1
                logger.warning("Failed to aggregate GitHub metrics for employee", employee_hash=emp_hash, error=str(e))
                continue

        result = {
            "status": "completed",
            "total_mapped_employees": len(mappings),
            "processed": processed,
            "skipped_no_github_username": skipped_no_user,
            "failed": failed,
            "week_start": str(week_start_date),
            "week_end": str(week_end)
        }
        logger.info("Batch GitHub aggregation completed", **result)
        return result
    finally:
        if owns_identity_db:
            identity_db.close()
        if owns_behavioral_db:
            behavioral_db.close()
        if owns_client:
            await client.close()

def main():
    parser = argparse.ArgumentParser(description="Manual GitHub Aggregation Task")
    parser.add_argument("--employee-hash", required=False, default=None, help="Unique employee hash")
    parser.add_argument("--github-username", required=False, default=None, help="GitHub username (not stored)")
    parser.add_argument("--week-start", required=True, type=datetime.date.fromisoformat, help="Week start date (YYYY-MM-DD)")
    parser.add_argument("--week-end", required=False, default=None, type=datetime.date.fromisoformat, help="Week end date (YYYY-MM-DD)")
    
    args = parser.parse_args()
    week_end = args.week_end or (args.week_start + datetime.timedelta(days=6))
    
    try:
        if args.employee_hash and args.github_username:
            asyncio.run(
                run_aggregation(
                    employee_hash=args.employee_hash,
                    github_username=args.github_username,
                    week_start_date=args.week_start,
                    week_end=week_end
                )
            )
        else:
            asyncio.run(
                run_all_employees_aggregation(
                    week_start_date=args.week_start,
                    week_end=week_end
                )
            )
    except Exception:
        sys.exit(1)

if __name__ == "__main__":
    main()
