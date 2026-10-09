from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import Optional, List
from app.database.models import IdentityMapping

class IdentityVaultRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, mapping: IdentityMapping) -> IdentityMapping:
        try:
            self.db.add(mapping)
            self.db.commit()
            self.db.refresh(mapping)
            return mapping
        except IntegrityError:
            self.db.rollback()
            raise ValueError("Mapping for this identifier/hash already exists.")

    def get_by_hash(self, employee_hash: str) -> Optional[IdentityMapping]:
        return self.db.query(IdentityMapping).filter(IdentityMapping.employee_hash == employee_hash).first()

    def list_all(self, skip: int = 0, limit: int = 100) -> List[IdentityMapping]:
        return self.db.query(IdentityMapping).offset(skip).limit(limit).all()
