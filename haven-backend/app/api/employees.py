from fastapi import APIRouter, Depends, HTTPException
from app.database.models import User, RoleEnum
from app.security.dependencies import require_employee_or_above
from app.dependencies import get_behavioral_db
from app.services.cache_service import CacheService, get_cache_service
from app.config import get_settings

router = APIRouter(prefix="/api/v1/employees", tags=["employees"])

@router.get("/{employee_hash}")
def get_employee_data(
    employee_hash: str, 
    current_user: User = Depends(require_employee_or_above),
    behavioral_db = Depends(get_behavioral_db),
    cache_service: CacheService = Depends(get_cache_service)
):
    # Enforce record ownership
    if current_user.role == RoleEnum.EMPLOYEE:
        if current_user.employee_hash != employee_hash:
            raise HTTPException(status_code=403, detail="Employees can only access their own records.")
            
    elif current_user.role == RoleEnum.MANAGER:
        from app.database.models import WeeklyEmployeeMetrics
        target_employee = behavioral_db.query(WeeklyEmployeeMetrics).filter(WeeklyEmployeeMetrics.employee_hash == employee_hash).first()
        if not target_employee or target_employee.department != current_user.department:
            raise HTTPException(status_code=403, detail="Managers can only access records for their department.")
    
    settings = get_settings()
    cache_key = f"dashboard:{employee_hash}"
    
    cached_data = cache_service.get(cache_key)
    if cached_data:
        return cached_data
        
    response_data = {"employee_hash": employee_hash, "data": "employee data record summary"}
    
    cache_service.set(cache_key, response_data, settings.cache_ttl_dashboard)
    return response_data
