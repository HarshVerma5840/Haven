import os
from sqlalchemy import create_engine, inspect, text
from app.config import get_settings

def report_counts():
    settings = get_settings()
    
    databases = {
        "Core Database (haven)": settings.database_url,
        "Identity Database (haven_identity)": settings.identity_database_url,
        "Behavioral Database (haven_behavioral)": settings.behavioral_database_url
    }
    
    print("=" * 60)
    print("HAVEN POSTGRESQL ISOLATION REPORT")
    print("=" * 60)
    
    for db_label, db_url in databases.items():
        print(f"\n{db_label}:")
        engine = create_engine(db_url)
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        if not tables:
            print("  No tables found.")
            continue
            
        for table in tables:
            try:
                with engine.connect() as conn:
                    result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
                    count = result.scalar()
                    print(f"  - {table}: {count} records")
            except Exception as e:
                print(f"  - {table}: [Error reading count: {e}]")
                
    print("\n" + "=" * 60)

if __name__ == "__main__":
    report_counts()
