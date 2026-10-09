import asyncio
from datetime import date, datetime, time
from zoneinfo import ZoneInfo
from typing import List, Optional, Set
import structlog

from app.config import get_settings
from app.schemas.github import GitHubWeeklyMetrics
from app.services.github_client import GitHubClient

logger = structlog.get_logger(__name__)

class GitHubMetricsExtractor:
    """
    Extracts GitHub activity metrics for a specific user within a given timeframe.
    
    Exact definitions:
    - After-hours commit: A commit where the author's timestamp, converted to the configured 
      working timezone, falls strictly before the workday start or strictly after the workday end.
    - Weekend commit: A commit where the author's timestamp, converted to the configured 
      working timezone, falls on a Saturday (5) or Sunday (6).
    - Review response time: The duration in hours between a pull request's creation time 
      and the time the user submitted their first review on that pull request during the reporting period.
    - Issue resolution time: The duration in hours between an issue's creation and its closure, 
      for closed issues created or assigned to the user within the reporting period. Open issues 
      do not contribute to this average.
    """
    def __init__(self, client: GitHubClient):
        self.client = client
        self.settings = get_settings()
        self.tz = ZoneInfo(self.settings.github_working_timezone)
        self.workday_start = time.fromisoformat(self.settings.github_workday_start)
        self.workday_end = time.fromisoformat(self.settings.github_workday_end)
        self.repos = self.settings.github_repositories

    def _parse_gh_time(self, ts: Optional[str]) -> Optional[datetime]:
        if not ts:
            return None
        try:
            return datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(self.tz)
        except ValueError:
            return None

    def _is_weekend(self, dt: datetime) -> bool:
        return dt.weekday() >= 5

    def _is_after_hours(self, dt: datetime) -> bool:
        t = dt.time()
        return t < self.workday_start or t > self.workday_end

    async def extract_weekly_metrics(self, username: str, start_date: date, end_date: date) -> GitHubWeeklyMetrics:
        start_dt = datetime.combine(start_date, time.min, tzinfo=self.tz)
        end_dt = datetime.combine(end_date, time.max, tzinfo=self.tz)
        
        start_iso = start_dt.astimezone(ZoneInfo("UTC")).isoformat().replace("+00:00", "Z")
        end_iso = end_dt.astimezone(ZoneInfo("UTC")).isoformat().replace("+00:00", "Z")
        
        commit_shas: Set[str] = set()
        commits_total = 0
        commits_after_hours = 0
        commits_weekend = 0
        
        pr_ids: Set[int] = set()
        issue_ids: Set[int] = set()
        
        pr_count = 0
        issue_count = 0
        
        review_count = 0
        review_response_times: List[float] = []
        issue_resolution_times: List[float] = []

        for repo in self.repos:
            # 1. Fetch Commits
            commits = await self.client.get_paginated(
                f"repos/{repo}/commits",
                params={"author": username, "since": start_iso, "until": end_iso}
            )
            for c in commits:
                sha = c.get("sha")
                if not sha or sha in commit_shas:
                    continue
                commit_shas.add(sha)
                
                commit_data = c.get("commit", {})
                author_data = commit_data.get("author", {})
                commit_date_str = author_data.get("date")
                
                dt = self._parse_gh_time(commit_date_str)
                if not dt:
                    continue
                
                if not (start_dt <= dt <= end_dt):
                    continue
                    
                commits_total += 1
                if self._is_weekend(dt):
                    commits_weekend += 1
                if self._is_after_hours(dt):
                    commits_after_hours += 1

            # 2. Fetch Issues and PRs
            issues = await self.client.get_paginated(
                f"repos/{repo}/issues",
                params={"state": "all", "since": start_iso}
            )
            
            for item in issues:
                item_id = item.get("id")
                created_at_str = item.get("created_at")
                created_dt = self._parse_gh_time(created_at_str)
                
                if not created_dt:
                    continue
                    
                creator = (item.get("user") or {}).get("login", "")
                is_pr = "pull_request" in item
                
                created_in_period = (start_dt <= created_dt <= end_dt)
                
                if is_pr:
                    if item_id not in pr_ids:
                        pr_ids.add(item_id)
                        
                        if created_in_period and creator.lower() == username.lower():
                            pr_count += 1
                            
                        # Fetch reviews for the PR
                        pr_number = item.get("number")
                        if pr_number:
                            reviews = await self.client.get_paginated(f"repos/{repo}/pulls/{pr_number}/reviews")
                            user_reviews = []
                            for r in reviews:
                                r_user = (r.get("user") or {}).get("login", "")
                                if r_user.lower() == username.lower():
                                    r_ts = self._parse_gh_time(r.get("submitted_at"))
                                    if r_ts and start_dt <= r_ts <= end_dt:
                                        user_reviews.append(r_ts)
                                        
                            if user_reviews:
                                review_count += len(user_reviews)
                                first_review_ts = min(user_reviews)
                                if first_review_ts >= created_dt:
                                    response_hours = (first_review_ts - created_dt).total_seconds() / 3600.0
                                    review_response_times.append(response_hours)
                else:
                    if item_id not in issue_ids:
                        issue_ids.add(item_id)
                        assignees = [a.get("login", "").lower() for a in (item.get("assignees") or [])]
                        
                        is_creator = (creator.lower() == username.lower())
                        is_assignee = (username.lower() in assignees)
                        
                        if (is_creator or is_assignee) and created_in_period:
                            issue_count += 1
                            
                            closed_at_str = item.get("closed_at")
                            if closed_at_str:
                                closed_dt = self._parse_gh_time(closed_at_str)
                                if closed_dt and closed_dt >= created_dt:
                                    res_hours = (closed_dt - created_dt).total_seconds() / 3600.0
                                    issue_resolution_times.append(res_hours)

        avg_review = (sum(review_response_times) / len(review_response_times)) if review_response_times else None
        avg_issue = (sum(issue_resolution_times) / len(issue_resolution_times)) if issue_resolution_times else None

        return GitHubWeeklyMetrics(
            github_username=username,
            week_start_date=start_date,
            github_commit_count=commits_total,
            after_hours_commit_count=commits_after_hours,
            weekend_commit_count=commits_weekend,
            pull_request_count=pr_count,
            review_count=review_count,
            review_response_hours=avg_review,
            issue_count=issue_count,
            issue_resolution_hours=avg_issue
        )
