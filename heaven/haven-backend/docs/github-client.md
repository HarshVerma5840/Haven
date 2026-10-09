# GitHub Client and Metrics Extractor

This document outlines the design, configuration, and behavior of the Haven backend GitHub integration.

## Configuration

The GitHub client behavior is strictly governed by environment variables loaded through `app.config.Settings`:

- `GITHUB_TOKEN`: The bearer token for GitHub API access (must have permissions for commits, issues, PRs, and reviews).
- `GITHUB_API_BASE_URL`: Defaults to `https://api.github.com`.
- `GITHUB_ORGANIZATION`: The target GitHub organization (if applicable).
- `GITHUB_REPOSITORIES`: A list of repository names to track (e.g., `["org/repo1", "org/repo2"]`).
- `GITHUB_REQUEST_TIMEOUT_SECONDS`: Request timeout per API call (default 30).
- `GITHUB_MAX_RETRIES`: Maximum number of retry attempts for transient errors (default 3).
- `GITHUB_WORKING_TIMEZONE`: Timezone for all date-time bound metrics (e.g., `America/New_York` or `UTC`).
- `GITHUB_WORKDAY_START`: Expected workday start time in `HH:MM` format (e.g., `09:00`).
- `GITHUB_WORKDAY_END`: Expected workday end time in `HH:MM` format (e.g., `17:00`).

## Supported Metrics

The `GitHubMetricsExtractor` aggregates the following metrics within a strict reporting period (`GitHubWeeklyMetrics`):

1. **Commit count**: Total commits authored by the user across configured repositories.
2. **After-hours commit count**: Commits authored strictly before `GITHUB_WORKDAY_START` or strictly after `GITHUB_WORKDAY_END` in the configured timezone.
3. **Weekend commit count**: Commits authored on a Saturday or Sunday in the configured timezone.
4. **Pull request count**: Total pull requests created by the user within the reporting period.
5. **Review count**: Total reviews submitted by the user on PRs updated within the reporting period.
6. **Average review response time**: The average duration in hours between a pull request's creation and the user's first review.
7. **Issue count**: Total issues created by or assigned to the user within the reporting period.
8. **Average issue resolution time**: The average duration in hours between an issue's creation and its closure (open issues are excluded).

## Reporting Period Behavior & Timezone Behavior

- The `start_date` and `end_date` are explicitly provided to the extractor.
- `start_date` is treated as `00:00:00` in `GITHUB_WORKING_TIMEZONE`.
- `end_date` is treated as `23:59:59.999999` in `GITHUB_WORKING_TIMEZONE`.
- All timestamps returned by GitHub (UTC) are localized to the configured timezone before evaluating conditions (e.g., "was this a weekend?").

## Missing-Data Policy

- If a user has no events, `0` is returned for all integer counts.
- For averages (`review_response_hours`, `issue_resolution_hours`), if there are no data points to compute an average (e.g., zero reviews or no closed issues), the explicit value is `None`.

## Retry and Rate-Limit Behavior

The `GitHubClient` implements exponential backoff and explicit retry handling:
- **Rate Limits (`403 Forbidden` with `x-ratelimit-remaining: "0"`)**: Throws `GitHubForbiddenError` immediately unless `retry-after` header is present. If `retry-after` is present and attempts remain, the client sleeps and retries.
- **Server Errors (`500`, `502`, `503`, `504`)**: The client sleeps (`0.01s` in test mode, exponential backoff in prod) and retries up to `GITHUB_MAX_RETRIES`.
- **Timeouts & Network Errors**: Retries up to `GITHUB_MAX_RETRIES` before raising `GitHubNetworkTimeoutError` or `GitHubUnexpectedAPIResponseError`.

## Known GitHub API Limitations

- The GitHub Issues API endpoint `/repos/{repo}/issues` returns both Issues and Pull Requests. PRs are identified by the presence of the `pull_request` key.
- Filtering by `since` only fetches issues/PRs *updated* since the timestamp. The extractor explicitly filters out entities whose `created_at` timestamp falls outside the reporting period.
- Review history is retrieved on a per-PR basis. PRs updated within the period are fetched, and their reviews are subsequently queried to detect the user's participation. This trades off a slightly higher API call volume (1 call per active PR) for accuracy.

## Example Usage from Python

```python
import asyncio
from datetime import date
from app.services.github_client import GitHubClient
from app.services.github_metrics import GitHubMetricsExtractor

async def main():
    # Transport dependencies are cleanly isolated
    client = GitHubClient()
    extractor = GitHubMetricsExtractor(client)
    
    try:
        metrics = await extractor.extract_weekly_metrics(
            username="octocat",
            start_date=date(2026, 10, 5),
            end_date=date(2026, 10, 11)
        )
        print(f"Total Commits: {metrics.github_commit_count}")
        print(f"After hours: {metrics.after_hours_commit_count}")
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(main())
```
