# add_debug_mode.py
# Database migration to add debug_mode field to companies table
# Location: web_services_product/api-server/migrations/add_debug_mode.py
#
# RUN THIS MIGRATION:
# Option 1: Direct SQL
#   psql -U postgres -d formfinder -f migrations/add_debug_mode.sql
#
# Option 2: Python script (run once)
#   cd api-server && python migrations/add_debug_mode.py

from sqlalchemy import text
from models.database import engine, SessionLocal


def upgrade():
    """Add debug_mode column to companies table"""
    db = SessionLocal()
    try:
        # Add column if it doesn't exist
        db.execute(text("""
            ALTER TABLE companies 
            ADD COLUMN IF NOT EXISTS debug_mode BOOLEAN DEFAULT FALSE;
        """))
        db.commit()
        print("[Migration] Added debug_mode column to companies table")
    except Exception as e:
        db.rollback()
        print(f"[Migration] Error: {e}")
    finally:
        db.close()


def downgrade():
    """Remove debug_mode column from companies table"""
    db = SessionLocal()
    try:
        db.execute(text("""
            ALTER TABLE companies DROP COLUMN IF EXISTS debug_mode;
        """))
        db.commit()
        print("[Migration] Removed debug_mode column from companies table")
    except Exception as e:
        db.rollback()
        print(f"[Migration] Error: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    upgrade()
