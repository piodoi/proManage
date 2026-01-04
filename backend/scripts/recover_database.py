"""
Database recovery script for corrupted SQLite database.

This script attempts to recover as much data as possible from a corrupted
SQLite database by dumping and recreating it.

Usage:
    python scripts/recover_database.py
    
Or with custom database path:
    python scripts/recover_database.py --db-path path/to/promanage.db
"""
import sqlite3
import shutil
import os
import argparse
from datetime import datetime


def backup_database(db_path: str) -> str:
    """Create a backup of the database before recovery."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{db_path}.backup_{timestamp}"
    try:
        shutil.copy2(db_path, backup_path)
        print(f"✓ Backup created: {backup_path}")
        return backup_path
    except Exception as e:
        print(f"✗ Failed to create backup: {e}")
        raise


def check_database_integrity(db_path: str) -> bool:
    """Check if database is corrupted."""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA integrity_check")
        result = cursor.fetchone()
        conn.close()
        
        if result[0] == "ok":
            print("✓ Database integrity check passed")
            return True
        else:
            print(f"✗ Database integrity check failed: {result[0]}")
            return False
    except sqlite3.DatabaseError as e:
        print(f"✗ Database is corrupted: {e}")
        return False


def recover_database(db_path: str) -> bool:
    """Attempt to recover a corrupted database."""
    recovered_path = f"{db_path}.recovered"
    dump_path = f"{db_path}.sql"
    
    try:
        print("\n=== Starting Database Recovery ===\n")
        
        # Step 1: Try to dump the database
        print("Step 1: Dumping database to SQL...")
        try:
            with open(dump_path, 'w', encoding='utf-8') as f:
                conn = sqlite3.connect(db_path)
                for line in conn.iterdump():
                    f.write(f"{line}\n")
                conn.close()
            print(f"✓ Database dumped to: {dump_path}")
        except Exception as e:
            print(f"✗ Failed to dump database: {e}")
            return False
        
        # Step 2: Create new database from dump
        print("\nStep 2: Creating new database from dump...")
        try:
            if os.path.exists(recovered_path):
                os.remove(recovered_path)
            
            conn = sqlite3.connect(recovered_path)
            cursor = conn.cursor()
            
            with open(dump_path, 'r', encoding='utf-8') as f:
                sql_script = f.read()
                cursor.executescript(sql_script)
            
            conn.commit()
            conn.close()
            print(f"✓ New database created: {recovered_path}")
        except Exception as e:
            print(f"✗ Failed to create new database: {e}")
            return False
        
        # Step 3: Verify recovered database
        print("\nStep 3: Verifying recovered database...")
        if not check_database_integrity(recovered_path):
            print("✗ Recovered database failed integrity check")
            return False
        
        # Step 4: Count records
        print("\nStep 4: Counting records in recovered database...")
        try:
            conn = sqlite3.connect(recovered_path)
            cursor = conn.cursor()
            
            tables = ['users', 'properties', 'renters', 'bills', 'payments']
            for table in tables:
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    count = cursor.fetchone()[0]
                    print(f"  {table}: {count} records")
                except sqlite3.OperationalError:
                    print(f"  {table}: table doesn't exist")
            
            conn.close()
        except Exception as e:
            print(f"✗ Failed to count records: {e}")
        
        print("\n=== Recovery Complete ===\n")
        print(f"Original (corrupted): {db_path}")
        print(f"Backup: {db_path}.backup_*")
        print(f"Recovered: {recovered_path}")
        print(f"SQL dump: {dump_path}")
        print("\nTo use the recovered database:")
        print(f"1. Stop your application")
        print(f"2. mv {db_path} {db_path}.corrupted")
        print(f"3. mv {recovered_path} {db_path}")
        print(f"4. Start your application")
        
        return True
        
    except Exception as e:
        print(f"✗ Recovery failed: {e}")
        return False


def enable_wal_mode(db_path: str):
    """Enable WAL mode on the database."""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("\nEnabling WAL mode and optimizations...")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA busy_timeout=30000")
        cursor.execute("PRAGMA temp_store=MEMORY")
        cursor.execute("PRAGMA mmap_size=268435456")
        cursor.execute("PRAGMA cache_size=-64000")
        
        # Check current mode
        cursor.execute("PRAGMA journal_mode")
        mode = cursor.fetchone()[0]
        print(f"✓ Journal mode set to: {mode}")
        
        conn.close()
    except Exception as e:
        print(f"✗ Failed to enable WAL mode: {e}")


def main():
    parser = argparse.ArgumentParser(description="Recover corrupted SQLite database")
    parser.add_argument(
        "--db-path",
        default="promanage.db",
        help="Path to database file (default: promanage.db)"
    )
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Skip creating backup (not recommended)"
    )
    parser.add_argument(
        "--enable-wal",
        action="store_true",
        help="Only enable WAL mode without recovery"
    )
    
    args = parser.parse_args()
    db_path = args.db_path
    
    if not os.path.exists(db_path):
        print(f"✗ Database file not found: {db_path}")
        return 1
    
    # If only enabling WAL mode
    if args.enable_wal:
        enable_wal_mode(db_path)
        return 0
    
    # Check if database is already okay
    if check_database_integrity(db_path):
        print("\nDatabase appears to be healthy.")
        response = input("Do you want to enable WAL mode anyway? (y/n): ")
        if response.lower() == 'y':
            enable_wal_mode(db_path)
        return 0
    
    # Create backup unless explicitly skipped
    if not args.no_backup:
        try:
            backup_database(db_path)
        except Exception:
            response = input("\nContinue without backup? (y/n): ")
            if response.lower() != 'y':
                return 1
    
    # Attempt recovery
    success = recover_database(db_path)
    
    if success:
        print("\n✓ Recovery successful!")
        return 0
    else:
        print("\n✗ Recovery failed!")
        print("\nYou may need to restore from an external backup or recreate the database.")
        return 1


if __name__ == "__main__":
    exit(main())

