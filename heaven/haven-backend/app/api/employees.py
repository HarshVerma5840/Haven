from fastapi import APIRouter, Depends, HTTPException
from app.database.models import User, RoleEnum
from app.security.dependencies import require_employee_or_above

router = APIRouter(prefix="/api/v1/employees", tags=["employees"])

@router.get("/{employee_hash}")
def get_employee_data(employee_hash: str, current_user: User = Depends(require_employee_or_above)):
    # Enforce record ownership
    if current_user.role == RoleEnum.EMPLOYEE:
        if current_user.employee_hash != employee_hash:
            raise HTTPException(status_code=403, detail="Employees can only access their own records.")
            
    elif current_user.role == RoleEnum.MANAGER:
        # In a real app we'd query the DB to ensure this employee_hash belongs to current_user.department
        # For now, we allow the route to process but log/validate logic will be expanded here.
        pass
        
    return {"employee_hash": employee_hash, "data": "employee data record"}
