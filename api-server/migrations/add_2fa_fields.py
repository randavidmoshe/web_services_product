"""
Migration: Add 2FA fields to users, super_admins, and companies tables

Run with: docker-compose exec api-server python migrations/add_2fa_fields.py
Rollback:  docker-compose exec api-server python migrations/add_2fa_fields.py rollback
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:password@db:5432/formfinder")


def run_migration():
    """Add 2FA columns to existing tables"""
    engine = create_engine(DATABASE_URL)
    
    migrations = [
        """
        ALTER TABLE users 
        ADD COLUMN IF NOT EXISTS totp_secret VARCHAR(255) NULL,
        ADD COLUMN IF NOT EXISTS totp_enabled BOOLEAN DEFAULT FALSE;
        """,
        """
        ALTER TABLE super_admins 
        ADD COLUMN IF NOT EXISTS totp_secret VARCHAR(255) NULL,
        ADD COLUMN IF NOT EXISTS totp_enabled BOOLEAN DEFAULT FALSE;
        """,
        """
        ALTER TABLE companies 
        ADD COLUMN IF NOT EXISTS require_2fa BOOLEAN DEFAULT FALSE;
        """,
    ]
    
    with engine.connect() as conn:
        for migration in migrations:
            try:
                conn.execute(text(migration))
                conn.commit()
                print(f"✅ Executed migration")
            except Exception as e:
                print(f"⚠️ Note: {e}")
                conn.rollback()
    
    print("\n✅ 2FA migration completed!")


def rollback_migration():
    """Remove 2FA columns"""
    engine = create_engine(DATABASE_URL)
    
    rollbacks = [
        "ALTER TABLE users DROP COLUMN IF EXISTS totp_secret, DROP COLUMN IF EXISTS totp_enabled;",
        "ALTER TABLE super_admins DROP COLUMN IF EXISTS totp_secret, DROP COLUMN IF EXISTS totp_enabled;",
        "ALTER TABLE companies DROP COLUMN IF EXISTS require_2fa;",
    ]
    
    with engine.connect() as conn:
        for rollback in rollbacks:
            try:
                conn.execute(text(rollback))
                conn.commit()
                print(f"✅ Rolled back")
            except Exception as e:
                print(f"⚠️ Note: {e}")
                conn.rollback()
    
    print("\n✅ 2FA rollback completed!")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "rollback":
        rollback_migration()
    else:
        run_migration()
