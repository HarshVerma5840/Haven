import pytest
import os
import csv
from datetime import date
from pydantic import ValidationError

from app.schemas.metrics import WeeklyEmployeeMetricsInput
from app.services.dataset_service import DatasetService

@pytest.fixture
def dataset_service():
    return DatasetService()

@pytest.fixture
def valid_record():
    return WeeklyEmployeeMetricsInput(
        employee_hash="hash_123",
        week_start_date=date(2026, 10, 5),
        github_commit_count=5,
        burnout_score=0.8,
        burnout_risk="High",
        schema_version="1.0",
        label_source="synthetic"
    )

def test_valid_records(dataset_service, valid_record):
    validated = dataset_service.validate_records([valid_record])
    assert len(validated) == 1
    assert validated[0].employee_hash == "hash_123"

def test_invalid_ranges(dataset_service, valid_record):
    invalid_dict = valid_record.model_dump()
    invalid_dict["github_commit_count"] = -5 # Invalid negative count
    
    with pytest.raises(ValueError, match="Record at index 0 failed validation"):
        dataset_service.validate_records([invalid_dict])

def test_duplicate_records(dataset_service, valid_record):
    duplicate = valid_record.model_copy()
    
    with pytest.raises(ValueError, match="Duplicate record found"):
        dataset_service.validate_records([valid_record, duplicate])

def test_missing_values_preservation(dataset_service):
    # Missing values should stay None (NULL)
    record = WeeklyEmployeeMetricsInput(
        employee_hash="hash_123",
        week_start_date=date(2026, 10, 5)
    )
    assert record.github_commit_count is None
    assert record.department is None
    
    validated = dataset_service.validate_record(record)
    assert validated.github_commit_count is None

def test_missing_averages_conversion(dataset_service):
    invalid_dict = {
        "employee_hash": "hash_123",
        "week_start_date": "2026-10-05",
        "review_count": 0,
        "review_response_hours": 0.0 # Should be None when count is 0
    }
    
    with pytest.raises(ValueError, match="cannot be 0.0 when review_count is 0"):
        dataset_service.validate_record(invalid_dict)

def test_target_consistency(dataset_service, valid_record):
    # Valid is score=0.8, risk="High"
    dataset_service.validate_record(valid_record)
    
    inconsistent = valid_record.model_copy()
    inconsistent.burnout_score = 0.8
    inconsistent.burnout_risk = "Low"
    
    with pytest.raises(ValueError, match="burnout_risk 'Low' requires burnout_score <= 0.4"):
        dataset_service.validate_record(inconsistent)

def test_calculate_data_completeness(dataset_service, valid_record):
    # Has a few fields set, many None
    ratio = dataset_service.calculate_data_completeness(valid_record)
    assert 0.0 < ratio < 1.0

def test_csv_export_and_ordering(dataset_service, valid_record, tmp_path):
    output_path = str(tmp_path / "exports" / "data.csv")
    dataset_service.export_records_to_csv([valid_record], output_path)
    
    assert os.path.exists(output_path)
    
    with open(output_path, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        headers = next(reader)
        row = next(reader)
        
        # Check column ordering
        assert headers == dataset_service.export_headers
        assert headers[0] == "employee_hash"
        
        # Check sensitive values not present
        # The schema doesn't even have github_username, but this ensures no accidental leakage
        assert "github_username" not in headers
        assert "testuser" not in row
