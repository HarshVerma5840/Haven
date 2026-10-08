import argparse
import asyncio
import datetime
import sys
import structlog

from app.config import get_settings
from app.database.connection import SessionLocal
from app.services.github_client import GitHubClient
from app.services.github_metrics import GitHubMetricsExtractor
from app.services.aggregation_service import AggregationService, AggregationError

logger = structlog.get_logger(__name__)

async def run_aggregation(
    employee_hash: str,
    github_username: str,
    week_start_date: datetime.date,
    week_end: datetime.date
):
    settings = get_settings()
    
    # Initialize dependencies
    client = GitHubClient()
    extractor = GitHubMetricsExtractor(client)
    
    db = SessionLocal()
    
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
        db.close()
        await client.close()

def main():
    parser = argparse.ArgumentParser(description="Manual GitHub Aggregation Task")
    parser.add_argument("--employee-hash", required=True, help="Unique employee hash")
    parser.add_argument("--github-username", required=True, help="GitHub username (not stored)")
    parser.add_argument("--week-start", required=True, type=datetime.date.fromisoformat, help="Week start date (YYYY-MM-DD)")
    parser.add_argument("--week-end", required=True, type=datetime.date.fromisoformat, help="Week end date (YYYY-MM-DD)")
    
    args = parser.parse_args()
    
    try:
        asyncio.run(
            run_aggregation(
                employee_hash=args.employee_hash,
                github_username=args.github_username,
                week_start_date=args.week_start,
                week_end=args.week_end
            )
        )
    except Exception:
        sys.exit(1)

if __name__ == "__main__":
    main()
