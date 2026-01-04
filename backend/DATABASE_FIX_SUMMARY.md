# 🚨 Database Corruption - Root Cause & Fix

## What Was Wrong

Your SQLite database was configured with **unsafe settings** that led to repeated corruption:

### Critical Issues
1. **No WAL Mode** ❌
   - Using default DELETE journal mode (not safe for concurrent access)
   - Every write locks entire database
   
2. **Unsafe Threading** ❌
   - `check_same_thread: False` without proper safeguards
   - Multiple connections can write simultaneously → corruption
   
3. **No Connection Pooling** ❌
   - No limit on concurrent connections
   - Race conditions during writes
   
4. **No Timeouts** ❌
   - No busy timeout = immediate failure on lock
   - Can corrupt database if interrupted

## What Was Fixed ✅

### Updated `backend/app/database.py`

**Before:**
```python
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    pool_pre_ping=True,
)
```

**After:**
```python
engine = create_engine(
    DATABASE_URL,
    connect_args={
        "check_same_thread": False,
        "timeout": 30.0,  # Wait for locks
    },
    pool_pre_ping=True,
    poolclass=QueuePool,  # Connection pooling
    pool_size=1,  # Single connection for SQLite
    max_overflow=0,  # No overflow
)

# Enable WAL mode + optimizations
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_conn, connection_record):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")  # CRITICAL FIX
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.execute("PRAGMA busy_timeout=30000")
    cursor.execute("PRAGMA temp_store=MEMORY")
    cursor.execute("PRAGMA mmap_size=268435456")
    cursor.execute("PRAGMA cache_size=-64000")
    cursor.close()
```

## What to Do Now

### Step 1: Recover Your Database

```bash
cd C:\projects\proManage\backend
python scripts\recover_database.py
```

This will:
- ✅ Create backup of corrupted database
- ✅ Dump and recreate database
- ✅ Verify integrity
- ✅ Show you how to use recovered database

### Step 2: Use Recovered Database

Follow the instructions from the recovery script:
```bash
# Stop the application if running (Ctrl+C)

# Rename corrupted database
mv promanage.db promanage.db.corrupted

# Use recovered database
mv promanage.db.recovered promanage.db

# Start application
poetry run uvicorn app.main:app
```

### Step 3: Verify WAL Mode is Active

After starting the app, check:
```bash
# Should see promanage.db-wal file now
dir promanage.db*
```

You should see:
- `promanage.db` - main database
- `promanage.db-wal` - Write-Ahead Log (good!)
- `promanage.db-shm` - Shared memory (good!)

## New Tools Available

### 1. Database Recovery Script
```bash
python scripts\recover_database.py
```

### 2. Automated Backup Script
```bash
# Create backup
python scripts\backup_database.py

# List backups
python scripts\backup_database.py --list

# Custom retention (keep 14 days)
python scripts\backup_database.py --keep 14
```

### 3. Enable WAL on Existing Database
```bash
python scripts\recover_database.py --enable-wal
```

## Why This Won't Happen Again

1. **WAL Mode** ✅
   - Readers don't block writers
   - Writers don't block readers
   - Better crash recovery
   
2. **Single Connection Pool** ✅
   - Prevents concurrent write conflicts
   - Serializes database access
   
3. **30-Second Timeout** ✅
   - Waits for locks instead of failing
   - More resilient to brief contentions
   
4. **Optimized Settings** ✅
   - Larger cache (64MB)
   - Memory-mapped I/O (256MB)
   - Better performance

## Prevention Tips

### ✅ DO
- Keep database on local SSD
- Run regular backups (use script)
- Shut down gracefully (Ctrl+C)
- Keep 1GB+ disk space free

### ❌ DON'T
- Store on OneDrive/Dropbox/Network drives
- Kill app with Task Manager
- Run multiple instances
- Edit database while app running

## For Production

Consider PostgreSQL for production:
```bash
# .env
DATABASE_URL=postgresql://user:password@localhost/promanage
```

All the same code works - just change the connection string!

## Summary

**Root Cause**: Unsafe SQLite configuration allowing concurrent writes without proper locking

**Solution**: WAL mode + single connection pool + timeouts + optimizations

**Result**: Database corruption should not happen again ✅

**Recovery**: Use provided scripts to recover data and enable new settings

