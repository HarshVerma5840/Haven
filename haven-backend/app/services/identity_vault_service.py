from typing import Optional, List

from app.database.models import IdentityMapping
from app.schemas.vault import IdentityMappingCreate, IdentityMappingResponse
from app.services.identity_service import IdentityService
from app.database.repositories.identity_vault_repository import IdentityVaultRepository
from app.security.encryption import encrypt_value, decrypt_value
import structlog

logger = structlog.get_logger(__name__)

class IdentityVaultService:
    def __init__(self, repository: IdentityVaultRepository, identity_service: IdentityService):
        self.repository = repository
        self.identity_service = identity_service

    def _decrypt_mapping(self, mapping: Optional[IdentityMapping]) -> Optional[IdentityMapping]:
        """Decrypts a mapping in memory without committing back to DB."""
        if not mapping:
            return None
        # Create a transient copy to avoid overwriting the DB object if flushed
        decrypted = IdentityMapping(
            id=mapping.id,
            employee_hash=mapping.employee_hash,
            email=decrypt_value(mapping.email),
            github_username=decrypt_value(mapping.github_username),
            hrms_employee_id=decrypt_value(mapping.hrms_employee_id),
            created_at=mapping.created_at,
            updated_at=mapping.updated_at
        )
        return decrypted

    def create_mapping(self, mapping_in: IdentityMappingCreate) -> IdentityMapping:
        """
        Creates a new identity mapping. Uses the first available identifier to generate the employee_hash.
        Only accessible by HR_ADMIN.
        """
        identifier = mapping_in.email or mapping_in.github_username or mapping_in.hrms_employee_id
        if not identifier:
            raise ValueError("At least one identifier must be provided to create a mapping.")
            
        employee_hash = self.identity_service.hash_identity(identifier)
        
        mapping = IdentityMapping(
            employee_hash=employee_hash,
            email=encrypt_value(mapping_in.email),
            github_username=encrypt_value(mapping_in.github_username),
            hrms_employee_id=encrypt_value(mapping_in.hrms_employee_id)
        )
        
        saved = self.repository.create(mapping)
        logger.info("Created new identity mapping", employee_hash=employee_hash)
        return self._decrypt_mapping(saved)

    def get_mapping_by_hash(self, employee_hash: str) -> Optional[IdentityMapping]:
        mapping = self.repository.get_by_hash(employee_hash)
        return self._decrypt_mapping(mapping)

    def list_mappings(self, skip: int = 0, limit: int = 100) -> List[IdentityMapping]:
        mappings = self.repository.list_all(skip, limit)
        return [self._decrypt_mapping(m) for m in mappings if m]
