"""
Database backup script with automated rotation.

Usage:
    python scripts/backup_database.py
    
Or with custom settings:
    python scripts/backup_database.py --db-path promanage.db --backup-dir backups --keep 7
"""
import sqlite3
import shutil
import os
import argparse
from datetime import datetime
from pathlib import Path


def create_backup(db_path: str, backup_dir: str) -> str:
    """Create a timestamped backup of the database."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"promanage_{timestamp}.db"
    backup_path = os.path.join(backup_dir, backup_filename)
    
    # Ensure backup directory exists
    os.makedirs(backup_dir, exist_ok=True)
    
    try:
        # Use SQLite backup API for safe backup (even while database is in use)
        source_conn = sqlite3.connect(db_path)
        backup_conn = sqlite3.connect(backup_path)
        
        with backup_conn:
            source_conn.backup(backup_conn)
        
        source_conn.close()
        backup_conn.close()
        
        # Get file size
        size_mb = os.path.getsize(backup_path) / (1024 * 1024)
        
        print(f"✓ Backup created: {backup_path} ({size_mb:.2f} MB)")
        return backup_path
        
    except Exception as e:
        print(f"✗ Backup failed: {e}")
        raise


def rotate_backups(backup_dir: str, keep: int):
    """Keep only the N most recent backups."""
    try:
        # Get all backup files
        backup_files = sorted(
            Path(backup_dir).glob("promanage_*.db"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )
        
        # Delete old backups
        deleted = 0
        for old_backup in backup_files[keep:]:
            os.remove(old_backup)
            deleted += 1
            print(f"  Deleted old backup: {old_backup.name}")
        
        if deleted > 0:
            print(f"✓ Removed {deleted} old backup(s)")
        else:
            print(f"✓ All backups within retention limit ({keep})")
            
    except Exception as e:
        print(f"✗ Failed to rotate backups: {e}")


def verify_backup(backup_path: str) -> bool:
    """Verify the backup is not corrupted."""
    try:
        conn = sqlite3.connect(backup_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA integrity_check")
        result = cursor.fetchone()
        conn.close()
        
        if result[0] == "ok":
            print(f"✓ Backup verified: {backup_path}")
            return True
        else:
            print(f"✗ Backup verification failed: {result[0]}")
            return False
            
    except Exception as e:
        print(f"✗ Backup verification failed: {e}")
        return False


def list_backups(backup_dir: str):
    """List all existing backups."""
    try:
        backup_files = sorted(
            Path(backup_dir).glob("promanage_*.db"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )
        
        if not backup_files:
            print("No backups found.")
            return
        
        print(f"\nExisting backups in {backup_dir}:")
        print("-" * 80)
        total_size = 0
        
        for backup_file in backup_files:
            stat = backup_file.stat()
            size_mb = stat.st_mtime / (1024 * 1024)
            modified = datetime.fromtimestamp(stat.st_mtime)
            total_size += stat.st_size
            
            print(f"  {backup_file.name:40s}  {size_mb:8.2f} MB  {modified:%Y-%m-%d %H:%M:%S}")
        
        print("-" * 80)
        print(f"Total: {len(backup_files)} backup(s), {total_size / (1024 * 1024):.2f} MB")
        
    except Exception as e:
        print(f"✗ Failed to list backups: {e}")


def main():
    parser = argparse.ArgumentParser(description="Backup SQLite database with rotation")
    parser.add_argument(
        "--db-path",
        default="promanage.db",
        help="Path to database file (default: promanage.db)"
    )
    parser.add_argument(
        "--backup-dir",
        default="backups",
        help="Backup directory (default: backups)"
    )
    parser.add_argument(
        "--keep",
        type=int,
        default=7,
        help="Number of backups to keep (default: 7)"
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List existing backups"
    )
    parser.add_argument(
        "--no-verify",
        action="store_true",
        help="Skip backup verification"
    )
    
    args = parser.parse_args()
    
    # List backups if requested
    if args.list:
        list_backups(args.backup_dir)
        return 0
    
    # Check if database exists
    if not os.path.exists(args.db_path):
        print(f"✗ Database file not found: {args.db_path}")
        return 1
    
    print(f"=== Database Backup ===\n")
    print(f"Database: {args.db_path}")
    print(f"Backup directory: {args.backup_dir}")
    print(f"Retention: {args.keep} backup(s)\n")
    
    # Create backup
    try:
        backup_path = create_backup(args.db_path, args.backup_dir)
        
        # Verify backup
        if not args.no_verify:
            if not verify_backup(backup_path):
                print("\n✗ Backup verification failed! Backup may be corrupted.")
                return 1
        
        # Rotate old backups
        rotate_backups(args.backup_dir, args.keep)
        
        print("\n✓ Backup complete!")
        return 0
        
    except Exception as e:
        print(f"\n✗ Backup failed: {e}")
        return 1


if __name__ == "__main__":
    exit(main())

