import csv
import os
from typing import List, Dict, Any, Union
from collections import Counter
from pydantic import ValidationError

from app.schemas.metrics import WeeklyEmployeeMetricsInput

class DatasetService:
    def __init__(self):
        # We define headers for CSV export to enforce stable column ordering.
        self.export_headers = [
            "employee_hash", "week_start_date", "department", "designation",
            "employment_type", "tenure_months", "team_size", "avg_daily_work_hours",
            "overtime_hours", "late_entry_count", "early_exit_count",
            "missing_checkout_count", "weekend_work_days", "holiday_work_days",
            "consecutive_work_days", "night_shift_count", "shift_change_count",
            "leave_days_taken", "unused_leave_balance", "unplanned_leave_count",
            "leave_cancellation_count", "timesheet_hours", "timesheet_correction_count",
            "workload_change_percent", "github_commit_count", "after_hours_commit_count",
            "weekend_commit_count", "pull_request_count", "review_count",
            "review_response_hours", "issue_count", "issue_resolution_hours",
            "appraisal_rating", "goal_completion_percent", "grievance_count",
            "grievance_resolution_days", "travel_days", "payroll_issue_count",
            "burnout_score", "burnout_risk", "schema_version", "data_completeness",
            "source_timestamp", "label_source"
        ]

    def validate_record(self, record: Union[Dict[str, Any], WeeklyEmployeeMetricsInput]) -> WeeklyEmployeeMetricsInput:
        """
        Validates a single record using the Pydantic schema and custom target rules.
        """
        # Ensure it parses through Pydantic (catches negative ranges, type errors, bounds)
        if isinstance(record, dict):
            parsed_record = WeeklyEmployeeMetricsInput(**record)
        else:
            parsed_record = record

        # Rule: Do not silently convert missing averages to zero.
        # Check specific edge case if implemented logically (e.g. review_count == 0 -> response hours shouldn't arbitrarily be 0.0 unless it truly means 0.0)
        # We primarily rely on the user passing None to preserve nulls.
        if parsed_record.review_response_hours == 0.0 and parsed_record.review_count == 0:
            raise ValueError("review_response_hours cannot be 0.0 when review_count is 0. It should be missing (None).")

        # Validate target consistency (burnout risk vs burnout score)
        if parsed_record.burnout_score is not None and parsed_record.burnout_risk is not None:
            score = parsed_record.burnout_score
            risk = parsed_record.burnout_risk
            
            # Simple heuristic bounds for validation mapping
            if risk == "High" and score <= 0.7:
                raise ValueError("burnout_risk 'High' requires burnout_score > 0.7")
            elif risk == "Medium" and (score <= 0.4 or score > 0.7):
                raise ValueError("burnout_risk 'Medium' requires burnout_score between 0.4 and 0.7")
            elif risk == "Low" and score > 0.4:
                raise ValueError("burnout_risk 'Low' requires burnout_score <= 0.4")

        # Validate completeness constraints natively
        if parsed_record.data_completeness is not None:
            if not (0.0 <= parsed_record.data_completeness <= 1.0):
                raise ValueError("data_completeness must be between 0.0 and 1.0")
                
        if not parsed_record.schema_version:
            raise ValueError("schema_version is required")
        if not parsed_record.label_source:
            raise ValueError("label_source is required")

        return parsed_record

    def validate_records(self, records: List[Union[Dict[str, Any], WeeklyEmployeeMetricsInput]]) -> List[WeeklyEmployeeMetricsInput]:
        """
        Validates a batch of records, ensuring no duplicate employee-week pairs.
        """
        validated = []
        keys_seen = set()

        for idx, record in enumerate(records):
            try:
                valid_record = self.validate_record(record)
            except Exception as e:
                raise ValueError(f"Record at index {idx} failed validation: {str(e)}") from e

            # Check duplicates
            key = (valid_record.employee_hash, valid_record.week_start_date)
            if key in keys_seen:
                raise ValueError(f"Duplicate record found for {key[0]} at week {key[1]}")
            keys_seen.add(key)
            
            validated.append(valid_record)
            
        return validated

    def calculate_data_completeness(self, record: WeeklyEmployeeMetricsInput) -> float:
        """
        Calculates the completeness ratio of a record based on all standard fields.
        """
        data = record.model_dump(exclude_none=False)
        total_fields = len(self.export_headers)
        
        # Count non-None values
        present_fields = sum(1 for key in self.export_headers if data.get(key) is not None)
        
        return present_fields / total_fields

    def export_records_to_csv(self, records: List[WeeklyEmployeeMetricsInput], output_path: str):
        """
        Exports records to a CSV file with stable column ordering.
        Creates parent directories if necessary.
        """
        # Create parent directories
        directory = os.path.dirname(output_path)
        if directory:
            os.makedirs(directory, exist_ok=True)
            
        with open(output_path, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=self.export_headers)
            writer.writeheader()
            
            for record in records:
                # Ensure completeness is calculated if missing
                if record.data_completeness is None:
                    record.data_completeness = self.calculate_data_completeness(record)
                    
                data = record.model_dump(mode="json") # Serialize dates/etc properly
                
                # Double check no raw github names sneaked into the model dump conceptually
                if "github_username" in data:
                    del data["github_username"]
                    
                # Write stable ordered row
                row = {h: data.get(h) for h in self.export_headers}
                writer.writerow(row)
