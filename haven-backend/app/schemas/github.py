from pydantic import BaseModel, Field
from datetime import date
from typing import Optional

class GitHubWeeklyMetrics(BaseModel):
    github_username: str = Field(..., min_length=1, description="GitHub username")
    week_start_date: date = Field(..., description="Start date of the reporting week")
    
    github_commit_count: int = Field(default=0, ge=0, description="Total number of commits")
    after_hours_commit_count: int = Field(default=0, ge=0, description="Commits made outside working hours")
    weekend_commit_count: int = Field(default=0, ge=0, description="Commits made on weekends")
    
    pull_request_count: int = Field(default=0, ge=0, description="Total number of pull requests created")
    review_count: int = Field(default=0, ge=0, description="Total number of reviews submitted")
    review_response_hours: Optional[float] = Field(default=None, ge=0.0, description="Average review response time in hours")
    
    issue_count: int = Field(default=0, ge=0, description="Total number of issues assigned or created")
    issue_resolution_hours: Optional[float] = Field(default=None, ge=0.0, description="Average issue resolution time in hours")
