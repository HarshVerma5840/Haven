import os
import sys
import argparse
from sqlalchemy import create_engine, inspect
from app.config import get_settings
from alembic.config import Config
from alembic import command
import run_migrations

def repair_database(dry_run=False):
    settings = get_settings()
    
    if settings.app_env.lower() == "production":
        print("[ERROR] Refusing to run in production environment.")
        sys.exit(1)
        
    databases = {
        "haven": {
            "url": settings.database_url,
            "drop_tables": ["identity_mappings", "weekly_employee_metrics", "burnout_predictions"],
            "script_location": "migrations/versions/core"
        },
        "haven_identity": {
            "url": settings.identity_database_url,
            "drop_tables": ["users", "weekly_employee_metrics", "burnout_predictions"],
            "script_location": "migrations/versions/identity"
        },
        "haven_behavioral": {
            "url": settings.behavioral_database_url,
            "drop_tables": ["users", "identity_mappings"],
            "script_location": "migrations/versions/behavioral"
        }
    }
    
    print("Starting database repair process...")
    for db_name, db_info in databases.items():
        print(f"\nAnalyzing {db_name}...")
        engine = create_engine(db_info["url"])
        inspector = inspect(engine)
        existing_tables = set(inspector.get_table_names())
        
        tables_to_drop = [t for t in db_info["drop_tables"] if t in existing_tables]
        alembic_version_exists = 'alembic_version' in existing_tables
        
        print(f"Target database: {db_name}")
        print(f"Tables to drop (incorrect tables): {tables_to_drop or 'None'}")
        print(f"Tables to preserve (seeded/correct data): {existing_tables - set(db_info['drop_tables']) - {'alembic_version'}}")
        
        if dry_run:
            print(f"[DRY-RUN] Would drop tables {tables_to_drop} in {db_name}")
            if alembic_version_exists:
                print(f"[DRY-RUN] Would drop alembic_version and stamp head in {db_name}")
            print(f"[DRY-RUN] Would run migrations for {db_name}")
            continue
            
        with engine.connect() as conn:
            for table in tables_to_drop:
                print(f"Dropping table {table}...")
                conn.exec_driver_sql(f"DROP TABLE IF EXISTS {table} CASCADE;")
                
            if alembic_version_exists:
                print("Dropping incorrect alembic_version...")
                conn.exec_driver_sql("DROP TABLE IF EXISTS alembic_version CASCADE;")
            conn.commit()
            
        # Stamp and upgrade
        base_dir = os.path.dirname(os.path.abspath(__file__))
        alembic_cfg = Config("alembic.ini")
        alembic_cfg.set_main_option("sqlalchemy.url", db_info["url"])
        alembic_cfg.set_main_option("version_locations", os.path.join(base_dir, db_info["script_location"]))
        alembic_cfg.attributes["current_db"] = db_name
        
        print(f"Stamping head for {db_name}...")
        command.stamp(alembic_cfg, "head")
        
        print(f"Re-running migrations for {db_name}...")
        command.upgrade(alembic_cfg, "head")
        
    print("\nRepair process complete.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Repair duplicated tables in development databases.")
    parser.add_argument("--reset-dev", action="store_true", help="Explicitly confirm the destructive repair.")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be dropped without executing.")
    
    args = parser.parse_args()
    
    if not args.reset_dev:
        print("[ERROR] Refusing to run without explicit --reset-dev flag.")
        sys.exit(1)
        
    repair_database(dry_run=args.dry_run)
