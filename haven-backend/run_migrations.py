import os
import sys
from alembic import command
from alembic.config import Config
from app.config import get_settings

def run_migrations():
    settings = get_settings()
    
    # Base Alembic config
    alembic_cfg = Config("alembic.ini")
    
    databases = {
        "haven": settings.database_url,
        "haven_identity": settings.identity_database_url,
        "haven_behavioral": settings.behavioral_database_url
    }
    
    for db_name, db_url in databases.items():
        print(f"Applying migrations to {db_name}...")
        # Override the URL in the alembic environment
        alembic_cfg.set_main_option("sqlalchemy.url", db_url)
        
        if db_name == "haven":
            alembic_cfg.set_main_option("version_locations", "migrations/versions/core")
        elif db_name == "haven_identity":
            alembic_cfg.set_main_option("version_locations", "migrations/versions/identity")
        elif db_name == "haven_behavioral":
            alembic_cfg.set_main_option("version_locations", "migrations/versions/behavioral")
            
        try:
            # Upgrade to head
            command.upgrade(alembic_cfg, "head")
            print(f"[OK] Migrations successfully applied to {db_name}")
        except Exception as e:
            print(f"[ERROR] Failed to apply migrations to {db_name}: {e}")
            sys.exit(1)

if __name__ == "__main__":
    run_migrations()
