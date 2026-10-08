from fastapi import APIRouter, Depends
from app.database.models import User
from app.security.dependencies import require_hr_admin

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])

@router.get("/")
def get_analytics(current_user: User = Depends(require_hr_admin)):
    # HR_ADMIN can access authorized aggregate HR analytics
    return {"message": "Authorized aggregate HR analytics"}
