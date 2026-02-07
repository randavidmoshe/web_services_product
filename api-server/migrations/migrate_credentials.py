#!/usr/bin/env python3
"""
Migrate plaintext credentials to KMS encryption.
Run inside api-server container.
"""
import os
import sys

sys.path.insert(0, '/app')

from models.database import SessionLocal, Network
from services.encryption_service import encrypt_credential


def is_encrypted(value: str) -> bool:
    """Check if value is already KMS encrypted."""
    if not value:
        return True
    return value.startswith('AQICA')


def migrate_credentials():
    db = SessionLocal()

    try:
        networks = db.query(Network).filter(
            (Network.login_username.isnot(None)) |
            (Network.login_password.isnot(None))
        ).all()

        migrated = 0
        skipped = 0

        for network in networks:
            needs_update = False

            # Check username
            if network.login_username and not is_encrypted(network.login_username):
                print(f"  Encrypting username for network {network.id} ({network.name})")
                network.login_username = encrypt_credential(
                    network.login_username,
                    network.company_id
                )
                needs_update = True

            # Check password
            if network.login_password and not is_encrypted(network.login_password):
                print(f"  Encrypting password for network {network.id} ({network.name})")
                network.login_password = encrypt_credential(
                    network.login_password,
                    network.company_id
                )
                needs_update = True

            if needs_update:
                migrated += 1
            else:
                skipped += 1

        db.commit()
        print(f"\nMigration complete: {migrated} networks updated, {skipped} already encrypted")

    except Exception as e:
        db.rollback()
        print(f"Migration failed: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print("Starting credential migration...")
    migrate_credentials()