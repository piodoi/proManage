# Database Maintenance Guide

## Common Issues and Solutions

### SQLite Database Corruption

If you see errors like:
- `database disk image is malformed`
- `database is locked`
- `UNIQUE constraint failed`

This indicates database corruption, usually caused by:
1. ❌ Concurrent writes without proper locking
2. ❌ Application crash during write operations
3. ❌ Disk full or I/O errors
4. ❌ File system issues (OneDrive, Dropbox, network drives)
5. ❌ Sudden power loss or system crash

## Fixed in This Update

✅ **WAL Mode Enabled**: Write-Ahead Logging prevents most corruption issues
✅ **Connection Pooling**: Single connection for SQLite prevents race conditions
✅ **Busy Timeout**: 30-second timeout for lock acquisition
✅ **Optimized Settings**: Memory-mapped I/O and larger cache for better performance

## Recovery Steps

### Option 1: Recover Existing Database (Recommended)

```bash
cd backend
python scripts/recover_database.py
```

This will:
1. Create a backup of your corrupted database
2. Attempt to dump and recreate the database
3. Verify the recovered database
4. Provide instructions for using the recovered database

### Option 2: Start Fresh

```bash
cd backend

# Backup your corrupted database (optional, for investigation)
mv promanage.db promanage.db.corrupted

# Delete the database file - it will be recreated on next startup
rm promanage.db promanage.db-shm promanage.db-wal

# Start the application - a fresh database will be created
poetry run uvicorn app.main:app
```

## Prevention: Regular Backups

### Manual Backup

```bash
cd backend
python scripts/backup_database.py
```

Options:
```bash
# List existing backups
python scripts/backup_database.py --list

# Custom backup directory and retention
python scripts/backup_database.py --backup-dir ~/db_backups --keep 14

# Skip verification (faster but not recommended)
python scripts/backup_database.py --no-verify
```

### Automated Backups (Linux/Mac)

Add to crontab:
```bash
# Daily backup at 3 AM, keep last 7 days
0 3 * * * cd /path/to/backend && python scripts/backup_database.py
```

### Automated Backups (Windows)

Use Task Scheduler:
1. Open Task Scheduler
2. Create Basic Task
3. Schedule: Daily at 3:00 AM
4. Action: Start a program
5. Program: `C:\path\to\python.exe`
6. Arguments: `scripts\backup_database.py`
7. Start in: `C:\path\to\backend`

## Enable WAL Mode on Existing Database

If you have a healthy database and just want to enable the new optimizations:

```bash
cd backend
python scripts/recover_database.py --enable-wal
```

## Best Practices

### ✅ DO

- ✅ Keep database on local SSD (not network drive, OneDrive, Dropbox)
- ✅ Run regular backups (automated if possible)
- ✅ Monitor disk space (ensure at least 1GB free)
- ✅ Use WAL mode (now enabled by default)
- ✅ Gracefully shutdown application (Ctrl+C, not kill -9)

### ❌ DON'T

- ❌ Don't store database on OneDrive/Dropbox/Google Drive
- ❌ Don't store database on network/SMB shares
- ❌ Don't kill application with Task Manager (use Ctrl+C)
- ❌ Don't run multiple instances accessing same database
- ❌ Don't edit database directly while application is running

## Migration to PostgreSQL (Production Recommended)

For production environments with multiple users or high concurrency, consider PostgreSQL:

1. Install PostgreSQL
2. Create database:
   ```sql
   CREATE DATABASE promanage;
   ```

3. Update `.env`:
   ```bash
   DATABASE_URL=postgresql://user:password@localhost/promanage
   ```

4. Restart application (tables will be created automatically)

## Monitoring Database Health

Check database integrity:
```bash
sqlite3 promanage.db "PRAGMA integrity_check"
```

Check current mode:
```bash
sqlite3 promanage.db "PRAGMA journal_mode"
```

Should show: `wal`

Check database size:
```bash
# Linux/Mac
ls -lh promanage.db*

# Windows
dir promanage.db*
```

## Troubleshooting

### Database Locked Errors

If you see "database is locked" errors:

1. Check for other processes accessing the database:
   ```bash
   # Linux/Mac
   lsof promanage.db
   
   # Windows
   handle.exe promanage.db
   ```

2. Increase busy timeout (already set to 30s in updated config)

3. Ensure no other application instances are running

### WAL Files Growing Large

WAL files (`.db-wal`) should auto-checkpoint. If they grow too large:

```bash
sqlite3 promanage.db "PRAGMA wal_checkpoint(TRUNCATE)"
```

### Performance Issues

1. Vacuum database (compacts and optimizes):
   ```bash
   sqlite3 promanage.db "VACUUM"
   ```

2. Analyze database (updates query planner statistics):
   ```bash
   sqlite3 promanage.db "ANALYZE"
   ```

## Support

If you continue to experience database issues:

1. Check the error logs
2. Verify disk space and permissions
3. Ensure database is on local storage
4. Try recovery script
5. Consider PostgreSQL for production

## Files Created by SQLite

- `promanage.db` - Main database file
- `promanage.db-wal` - Write-Ahead Log (temporary, auto-managed)
- `promanage.db-shm` - Shared Memory (temporary, auto-managed)

The `-wal` and `-shm` files are normal when using WAL mode and will be automatically managed by SQLite.

