# PostgreSQL Setup Guide - NexusFlow Digital FTE

## Problem
Your demo is falling back to in-memory storage because PostgreSQL is not running.

## Solution: 3 Simple Steps

---

## Step 1: Check if PostgreSQL is Installed

### Option A: Using Command Prompt
```cmd
psql --version
```

**If you see version number:** ✅ PostgreSQL is installed, skip to Step 2

**If you see "not recognized":** ❌ Install PostgreSQL:
1. Go to: https://www.postgresql.org/download/windows/
2. Click "Download the installer"
3. Run the installer
4. **Important:** Remember the password you set for `postgres` user!
5. Keep default port: `5432`

---

## Step 2: Start PostgreSQL Service

1. Press `Win + R`
2. Type: `services.msc`
3. Press Enter
4. Find service named: `postgresql-x64-14` or `postgresql-x64-15`
5. Right-click → **Start** (or Restart)
6. Status should show "Running"

---

## Step 3: Create Database and Tables

### Run the setup script:

```cmd
cd C:\Users\user\OneDrive\Desktop\hackhaton_five
python setup_postgres.py
```

This script will:
- ✅ Check PostgreSQL installation
- ✅ Test connection
- ✅ Create `nexusflow` database
- ✅ Load all tables (customers, tickets, messages, etc.)

---

## Step 4: Verify Connection

After setup, run the demo:

```cmd
python demo_api.py
```

**Look for this in the output:**

```
✅ Database operations module imported
🔌 Connecting to PostgreSQL...
✅ PostgreSQL connected
```

**If you see this, you're done!** 🎉

---

## Troubleshooting

### Error: "connection refused"
**Cause:** PostgreSQL service not running

**Fix:**
1. Open Services (`services.msc`)
2. Start `postgresql-x64-14` service

---

### Error: "password authentication failed"
**Cause:** Wrong password in `.env` file

**Fix:**
1. Open `.env` file
2. Update this line with your actual password:
   ```
   DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@localhost:5432/nexusflow
   ```
3. Save and restart `demo_api.py`

---

### Error: "database nexusflow does not exist"
**Cause:** Database not created yet

**Fix:** Run the setup script:
```cmd
python setup_postgres.py
```

---

## Quick Test

Once running, submit a test form at:
```
http://localhost:8000/support/form
```

Then verify data is in database:
```cmd
psql -U postgres -h localhost -d nexusflow -c "SELECT COUNT(*) FROM tickets;"
```

If you see a number (like `1`), **PostgreSQL is working!** ✅

---

## What You'll See When It Works

### On Server Startup:
```
✅ Database operations module imported
🔌 Connecting to PostgreSQL...
✅ PostgreSQL connected
```

### When Submitting Form:
```
✅ Data saved to PostgreSQL: ticket=TKT-20260331-002, conversation=abc-123
```

### Health Check (`/health`):
```json
{
  "status": "healthy",
  "database": "connected"
}
```

---

**Need help?** Run `python setup_postgres.py` - it will guide you through each step!
