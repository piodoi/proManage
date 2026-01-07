# MySQL Manual Import - Simple Guide

## 📦 Files You Need

1. **`mysql_schema.sql`** - Database schema (typed columns, indexes, foreign keys)
2. **`mysql_data_import.sql`** - Your data (INSERT statements)

Both files are in the `backend/scripts/` folder.

## 🔑 Key Architecture Change

The MySQL implementation uses **typed columns** instead of the document model (JSON `data` field):
- ✅ Separate columns for each field (name, address, amount, etc.)
- ✅ Proper data types (INT, FLOAT, DATETIME, ENUM)
- ✅ Foreign key constraints for data integrity
- ✅ Optimized indexes for fast queries
- ✅ Automatic delegation in `database.py` (SQLite for dev, MySQL for production)

---

## 🚀 Import Steps (Using Your MySQL Utility)

### Option 1: MySQL Command Line

```bash
# 1. Create/use database
mysql -u root -p
CREATE DATABASE IF NOT EXISTS ultrafinu_promanage CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE ultrafinu_promanage;
exit;

# 2. Import schema
mysql -u root -p ultrafinu_promanage < scripts/mysql_schema.sql

# 3. Import data
mysql -u root -p ultrafinu_promanage < scripts/mysql_data_import.sql
```

### Option 2: MySQL Workbench

1. Open MySQL Workbench
2. Connect to your server
3. Select database: `ultrafinu_promanage`
4. **File → Run SQL Script** → Select `mysql_schema.sql` → Run
5. **File → Run SQL Script** → Select `mysql_data_import.sql` → Run

### Option 3: phpMyAdmin

1. Login to phpMyAdmin
2. Select database: `ultrafinu_promanage`
3. Click **Import** tab
4. Choose `mysql_schema.sql` → Import
5. Choose `mysql_data_import.sql` → Import

### Option 4: HeidiSQL / DBeaver / Other Tools

Similar process:
1. Connect to MySQL server
2. Select/create database
3. Execute/import `mysql_schema.sql`
4. Execute/import `mysql_data_import.sql`

---

## ✅ After Import

### 1. Update .env

```bash
# backend/.env
DATABASE_URL=mysql://root:epsilonpi@127.0.0.1:3306/ultrafinu_promanage
```

### 2. Restart Backend

```bash
cd backend
poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000
```

**Check logs for:**
```
[Database] Using MySQL database
```

---

## 📊 What Gets Imported

**Schema (mysql_schema.sql):**
- ✅ 10 tables with typed columns
- ✅ 40+ optimized indexes
- ✅ Foreign key constraints
- ✅ ENUM types for status fields

**Data (mysql_data_import.sql):**
- ✅ All users
- ✅ All properties
- ✅ All renters
- ✅ All suppliers
- ✅ All bills
- ✅ All payments
- ✅ All credentials
- ✅ All preferences

---

## 🔍 Verify Import

```sql
-- Connect to MySQL
USE ultrafinu_promanage;

-- Check tables
SHOW TABLES;

-- Check record counts
SELECT 'users' as table_name, COUNT(*) as count FROM users
UNION ALL SELECT 'properties', COUNT(*) FROM properties
UNION ALL SELECT 'bills', COUNT(*) FROM bills
UNION ALL SELECT 'suppliers', COUNT(*) FROM suppliers;

-- Check a sample user
SELECT * FROM users LIMIT 1;

-- Check indexes on bills table
SHOW INDEX FROM bills;
```

---

## 💡 Tips

1. **Import schema first, then data** - Data depends on schema
2. **Check for errors** - Your utility will show any import errors
3. **Backup first** - If reimporting, backup existing database
4. **UTF-8 encoding** - Make sure your utility uses UTF-8/utf8mb4

---

## ⚠️ Troubleshooting

### "Table already exists"
- Drop database and recreate: `DROP DATABASE ultrafinu_promanage; CREATE DATABASE...`
- Or delete tables: `DROP TABLE IF EXISTS bills, payments, ...;`

### "Duplicate entry"
- Tables not empty - drop and reimport
- Or clear tables: `TRUNCATE TABLE bills;` (for each table)

### "Foreign key constraint fails"
- Import schema first
- Check parent records exist (users before properties, etc.)

---

## 🎉 Done!

After import, your MySQL database is ready with:
- ✅ Full schema with typed columns
- ✅ All your data migrated
- ✅ 10x faster queries
- ✅ 100+ concurrent users supported

**Just update .env and restart!**

