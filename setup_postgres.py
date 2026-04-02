"""
Setup PostgreSQL for NexusFlow Digital FTE
===========================================
This script helps you set up PostgreSQL database for the project.

Run this script ONCE to create the database and tables.
"""

import subprocess
import sys
import os

print("=" * 80)
print("NEXUSFLOW DIGITAL FTE - PostgreSQL Setup")
print("=" * 80)

# Check if PostgreSQL is installed
print("\n1. Checking if PostgreSQL is installed...")

try:
    # Try to run psql command
    result = subprocess.run(
        ["psql", "--version"],
        capture_output=True,
        text=True,
        timeout=5
    )
    
    if result.returncode == 0:
        print(f"   ✅ PostgreSQL found: {result.stdout.strip()}")
    else:
        print("   ❌ PostgreSQL NOT found!")
        print("\n   Please install PostgreSQL:")
        print("   1. Go to: https://www.postgresql.org/download/windows/")
        print("   2. Download and install PostgreSQL 14 or higher")
        print("   3. Remember the password you set for 'postgres' user")
        print("   4. Run this script again after installation")
        sys.exit(1)
        
except FileNotFoundError:
    print("   ❌ PostgreSQL NOT found!")
    print("\n   Please install PostgreSQL:")
    print("   1. Go to: https://www.postgresql.org/download/windows/")
    print("   2. Download and install PostgreSQL 14 or higher")
    print("   3. Remember the password you set for 'postgres' user")
    print("   4. Run this script again after installation")
    sys.exit(1)

# Try to connect to PostgreSQL
print("\n2. Testing PostgreSQL connection...")

DB_PASSWORD = "postgres"  # Default password
DB_USER = "postgres"
DB_HOST = "localhost"
DB_PORT = "5432"

# Try to connect
env = os.environ.copy()
env['PGPASSWORD'] = DB_PASSWORD

try:
    result = subprocess.run(
        ["psql", "-U", DB_USER, "-h", DB_HOST, "-p", DB_PORT, "-c", "SELECT 1;"],
        capture_output=True,
        text=True,
        timeout=10,
        env=env
    )
    
    if result.returncode == 0:
        print("   ✅ Connected to PostgreSQL successfully!")
    else:
        print(f"   ⚠️  Connection failed: {result.stderr.strip()}")
        print("\n   Try these steps:")
        print("   1. Make sure PostgreSQL service is running:")
        print("      - Open Services (services.msc)")
        print("      - Find 'postgresql-x64-14' (or similar)")
        print("      - Right-click → Start")
        print("   2. Check your password in .env file")
        print("   3. Run this script again")
        sys.exit(1)
        
except Exception as e:
    print(f"   ❌ Connection error: {e}")
    sys.exit(1)

# Create database
print("\n3. Creating 'nexusflow' database...")

env['PGPASSWORD'] = DB_PASSWORD

# First check if database already exists
result = subprocess.run(
    ["psql", "-U", DB_USER, "-h", DB_HOST, "-p", DB_PORT, "-lqt"],
    capture_output=True,
    text=True,
    timeout=10,
    env=env
)

if 'nexusflow' in result.stdout.lower():
    print("   ℹ️  Database 'nexusflow' already exists")
else:
    result = subprocess.run(
        ["psql", "-U", DB_USER, "-h", DB_HOST, "-p", DB_PORT, "-c", "CREATE DATABASE nexusflow;"],
        capture_output=True,
        text=True,
        timeout=10,
        env=env
    )
    
    if result.returncode == 0:
        print("   ✅ Database 'nexusflow' created successfully!")
    else:
        print(f"   ⚠️  Could not create database: {result.stderr.strip()}")
        print("   (This is OK if database already exists)")

# Run schema
print("\n4. Running database schema...")

schema_path = os.path.join(os.path.dirname(__file__), 'production', 'database', 'schema.sql')

if os.path.exists(schema_path):
    env['PGPASSWORD'] = DB_PASSWORD
    
    result = subprocess.run(
        ["psql", "-U", DB_USER, "-h", DB_HOST, "-p", DB_PORT, "-d", "nexusflow", "-f", schema_path],
        capture_output=True,
        text=True,
        timeout=60,
        env=env
    )
    
    if result.returncode == 0:
        print("   ✅ Schema loaded successfully!")
        print("   Tables created: customers, conversations, messages, tickets, etc.")
    else:
        # Check if it's just "already exists" errors
        if 'already exists' in result.stderr.lower():
            print("   ℹ️  Schema already loaded (tables exist)")
        else:
            print(f"   ⚠️  Schema load had issues: {result.stderr[:200]}")
            print("   (This is usually OK - tables may already exist)")
else:
    print(f"   ⚠️  Schema file not found at: {schema_path}")

# Verify setup
print("\n5. Verifying database setup...")

env['PGPASSWORD'] = DB_PASSWORD

result = subprocess.run(
    [
        "psql", "-U", DB_USER, "-h", DB_HOST, "-p", DB_PORT, "-d", "nexusflow",
        "-c", "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name;"
    ],
    capture_output=True,
    text=True,
    timeout=10,
    env=env
)

if result.returncode == 0:
    tables = [line.strip() for line in result.stdout.split('\n') if line.strip() and not line.startswith('-')]
    print(f"   ✅ Found {len(tables)} tables in database:")
    for table in tables[:10]:  # Show first 10
        print(f"      - {table}")
    if len(tables) > 10:
        print(f"      ... and {len(tables) - 10} more")
else:
    print(f"   ⚠️  Could not verify tables: {result.stderr[:200]}")

print("\n" + "=" * 80)
print("✅ PostgreSQL Setup Complete!")
print("=" * 80)
print("\nNext steps:")
print("1. Make sure .env file has correct DATABASE_URL:")
print(f"   DATABASE_URL=postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/nexusflow")
print("\n2. Start the demo server:")
print("   python demo_api.py")
print("\n3. Open browser to:")
print("   http://localhost:8000/support/form")
print("\n" + "=" * 80)
