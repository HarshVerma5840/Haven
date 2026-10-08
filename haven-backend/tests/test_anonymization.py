from app.database.models import WeeklyEmployeeMetrics

def test_behavioral_model_has_no_identity_fields():
    """
    Validates that the WeeklyEmployeeMetrics model does not contain any
    raw identity fields such as email, github_username, or hrms_employee_id.
    """
    forbidden_fields = ['email', 'github_username', 'hrms_employee_id', 'username']
    
    # Get all column names from the model
    columns = [column.name for column in WeeklyEmployeeMetrics.__table__.columns]
    
    # Ensure none of the forbidden fields exist in the columns
    for field in forbidden_fields:
        assert field not in columns, f"Forbidden field '{field}' found in behavioral model!"
        
    # Ensure employee_hash exists
    assert 'employee_hash' in columns, "employee_hash is missing from behavioral model!"
