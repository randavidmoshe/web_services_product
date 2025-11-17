#!/usr/bin/env python3
"""
Database Migration Manager
Location: web_services_product/database/migrate.py

Full migration system with:
- Auto-run new migrations
- Rollback support
- Automatic backups
- Migration history tracking
"""

import os
import sys
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from datetime import datetime
from pathlib import Path
import subprocess


class MigrationManager:
    def __init__(self, db_config: dict, migrations_dir: str = "migrations"):
        self.db_config = db_config
        self.migrations_dir = Path(migrations_dir)
        self.backup_dir = Path("backups")
        self.backup_dir.mkdir(exist_ok=True)
        
    def get_connection(self):
        """Get database connection"""
        return psycopg2.connect(
            host=self.db_config['host'],
            port=self.db_config['port'],
            database=self.db_config['database'],
            user=self.db_config['user'],
            password=self.db_config['password']
        )
    
    def ensure_migration_table(self):
        """Create migrations_history table if it doesn't exist"""
        conn = self.get_connection()
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS migrations_history (
                id SERIAL PRIMARY KEY,
                migration_id INTEGER UNIQUE NOT NULL,
                filename VARCHAR(255) NOT NULL,
                executed_at TIMESTAMP DEFAULT NOW(),
                rolled_back_at TIMESTAMP NULL,
                status VARCHAR(20) DEFAULT 'applied'
            )
        """)
        
        cursor.close()
        conn.close()
        print("✅ Migrations history table ready")
    
    def get_applied_migrations(self):
        """Get list of already applied migrations"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT migration_id, filename 
            FROM migrations_history 
            WHERE status = 'applied'
            ORDER BY migration_id
        """)
        
        applied = {row[0]: row[1] for row in cursor.fetchall()}
        cursor.close()
        conn.close()
        return applied
    
    def get_pending_migrations(self):
        """Get list of migrations that need to be run"""
        applied = self.get_applied_migrations()
        
        all_migrations = []
        for file in sorted(self.migrations_dir.glob("*_UP.sql")):
            # Extract migration ID from filename (e.g., "001_initial_UP.sql" -> 1)
            migration_id = int(file.stem.split('_')[0])
            if migration_id not in applied:
                all_migrations.append((migration_id, file.name))
        
        return all_migrations
    
    def create_backup(self):
        """Create database backup before migration"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = self.backup_dir / f"backup_{timestamp}.sql"
        
        print(f"📦 Creating backup: {backup_file}")
        
        try:
            cmd = [
                "pg_dump",
                "-h", self.db_config['host'],
                "-p", str(self.db_config['port']),
                "-U", self.db_config['user'],
                "-d", self.db_config['database'],
                "-f", str(backup_file)
            ]
            
            env = os.environ.copy()
            env['PGPASSWORD'] = self.db_config['password']
            
            subprocess.run(cmd, check=True, env=env)
            print(f"✅ Backup created: {backup_file}")
            return backup_file
        except Exception as e:
            print(f"❌ Backup failed: {e}")
            return None
    
    def restore_backup(self, backup_file: Path):
        """Restore database from backup"""
        print(f"⚠️  Restoring from backup: {backup_file}")
        
        try:
            cmd = [
                "psql",
                "-h", self.db_config['host'],
                "-p", str(self.db_config['port']),
                "-U", self.db_config['user'],
                "-d", self.db_config['database'],
                "-f", str(backup_file)
            ]
            
            env = os.environ.copy()
            env['PGPASSWORD'] = self.db_config['password']
            
            subprocess.run(cmd, check=True, env=env)
            print(f"✅ Restored from backup")
            return True
        except Exception as e:
            print(f"❌ Restore failed: {e}")
            return False
    
    def run_migration(self, migration_id: int, filename: str, create_backup: bool = True):
        """Run a single migration"""
        up_file = self.migrations_dir / filename
        
        if not up_file.exists():
            print(f"❌ Migration file not found: {up_file}")
            return False
        
        print(f"\n{'='*60}")
        print(f"Running migration {migration_id}: {filename}")
        print(f"{'='*60}")
        
        # Create backup first
        backup_file = None
        if create_backup:
            backup_file = self.create_backup()
            if not backup_file:
                print("⚠️  Backup failed. Continue anyway? (y/n): ", end='')
                if input().lower() != 'y':
                    return False
        
        # Read and execute migration
        try:
            with open(up_file, 'r') as f:
                sql = f.read()
            
            conn = self.get_connection()
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            cursor = conn.cursor()
            
            # Execute migration
            cursor.execute(sql)
            
            # Record in history
            cursor.execute("""
                INSERT INTO migrations_history (migration_id, filename, status)
                VALUES (%s, %s, 'applied')
            """, (migration_id, filename))
            
            cursor.close()
            conn.close()
            
            print(f"✅ Migration {migration_id} applied successfully")
            return True
            
        except Exception as e:
            print(f"❌ Migration {migration_id} failed: {e}")
            
            # Offer to restore from backup
            if backup_file:
                print("\n⚠️  Restore from backup? (y/n): ", end='')
                if input().lower() == 'y':
                    self.restore_backup(backup_file)
            
            return False
    
    def rollback_migration(self, migration_id: int):
        """Rollback a migration"""
        applied = self.get_applied_migrations()
        
        if migration_id not in applied:
            print(f"❌ Migration {migration_id} is not applied")
            return False
        
        filename = applied[migration_id]
        down_filename = filename.replace('_UP.sql', '_DOWN.sql')
        down_file = self.migrations_dir / down_filename
        
        if not down_file.exists():
            print(f"❌ Rollback file not found: {down_file}")
            print(f"   Cannot rollback migration {migration_id}")
            return False
        
        print(f"\n{'='*60}")
        print(f"Rolling back migration {migration_id}: {filename}")
        print(f"{'='*60}")
        
        # Create backup first
        backup_file = self.create_backup()
        if not backup_file:
            print("⚠️  Backup failed. Continue anyway? (y/n): ", end='')
            if input().lower() != 'y':
                return False
        
        # Read and execute rollback
        try:
            with open(down_file, 'r') as f:
                sql = f.read()
            
            conn = self.get_connection()
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            cursor = conn.cursor()
            
            # Execute rollback
            cursor.execute(sql)
            
            # Update history
            cursor.execute("""
                UPDATE migrations_history 
                SET status = 'rolled_back', rolled_back_at = NOW()
                WHERE migration_id = %s
            """, (migration_id,))
            
            cursor.close()
            conn.close()
            
            print(f"✅ Migration {migration_id} rolled back successfully")
            return True
            
        except Exception as e:
            print(f"❌ Rollback {migration_id} failed: {e}")
            
            if backup_file:
                print("\n⚠️  Restore from backup? (y/n): ", end='')
                if input().lower() == 'y':
                    self.restore_backup(backup_file)
            
            return False
    
    def migrate_up(self, create_backup: bool = True):
        """Run all pending migrations"""
        self.ensure_migration_table()
        
        pending = self.get_pending_migrations()
        
        if not pending:
            print("✅ No pending migrations")
            return True
        
        print(f"\n📋 Found {len(pending)} pending migration(s):")
        for migration_id, filename in pending:
            print(f"   {migration_id}: {filename}")
        
        print(f"\nProceed with migrations? (y/n): ", end='')
        if input().lower() != 'y':
            print("❌ Cancelled")
            return False
        
        # Run each migration
        for migration_id, filename in pending:
            success = self.run_migration(migration_id, filename, create_backup)
            if not success:
                print(f"\n❌ Migration stopped at {migration_id}")
                return False
        
        print(f"\n{'='*60}")
        print(f"✅ All migrations completed successfully")
        print(f"{'='*60}")
        return True
    
    def status(self):
        """Show migration status"""
        self.ensure_migration_table()
        
        applied = self.get_applied_migrations()
        pending = self.get_pending_migrations()
        
        print(f"\n{'='*60}")
        print("MIGRATION STATUS")
        print(f"{'='*60}\n")
        
        print(f"Applied migrations: {len(applied)}")
        for migration_id, filename in sorted(applied.items()):
            print(f"  ✅ {migration_id}: {filename}")
        
        print(f"\nPending migrations: {len(pending)}")
        for migration_id, filename in pending:
            print(f"  ⏳ {migration_id}: {filename}")
        
        print()


def main():
    """Main CLI interface"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Database Migration Manager')
    parser.add_argument('command', choices=['up', 'rollback', 'status'], 
                       help='Command to run')
    parser.add_argument('--migration-id', type=int, 
                       help='Migration ID for rollback')
    parser.add_argument('--no-backup', action='store_true',
                       help='Skip automatic backups (not recommended)')
    
    args = parser.parse_args()
    
    # Database configuration (from environment or defaults)
    db_config = {
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': int(os.getenv('DB_PORT', '5432')),
        'database': os.getenv('DB_NAME', 'form_discoverer'),
        'user': os.getenv('DB_USER', 'postgres'),
        'password': os.getenv('DB_PASSWORD', 'postgres')
    }
    
    manager = MigrationManager(db_config)
    
    if args.command == 'up':
        manager.migrate_up(create_backup=not args.no_backup)
    
    elif args.command == 'rollback':
        if not args.migration_id:
            print("❌ --migration-id required for rollback")
            sys.exit(1)
        manager.rollback_migration(args.migration_id)
    
    elif args.command == 'status':
        manager.status()


if __name__ == "__main__":
    main()
