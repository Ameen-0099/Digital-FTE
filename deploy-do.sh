#!/bin/bash
# DigitalOcean Deployment Script for NexusFlow Digital FTE
# =========================================================

set -e

# Configuration
PROJECT_NAME="nexusflow-fte"
GITHUB_REPO="YOUR_GITHUB_USERNAME/hackhaton_five"
REGION="nyc"
APP_SIZE="basic-xxs"
DB_SIZE="db-s-dev-database"

echo "========================================"
echo "NexusFlow Digital FTE - DO Deployment"
echo "========================================"
echo ""

# Step 1: Check doctl installation
echo "[1/8] Checking doctl installation..."
if ! command -v doctl &> /dev/null; then
    echo "❌ doctl not found. Install from: https://docs.digitalocean.com/reference/doctl/how-to/install/"
    exit 1
fi
echo "✅ doctl installed: $(doctl version)"

# Step 2: Authenticate
echo ""
echo "[2/8] Authenticating with DigitalOcean..."
doctl auth init
echo "✅ Authentication successful"

# Step 3: Create Project
echo ""
echo "[3/8] Setting up project..."
if doctl projects list --format "Name,ID" --no-header | grep -q "$PROJECT_NAME"; then
    echo "✅ Project exists"
else
    doctl projects create --name "$PROJECT_NAME" --purpose "web-application" --environment Development
    echo "✅ Project created"
fi

# Step 4: Create Database
echo ""
echo "[4/8] Creating Managed PostgreSQL Database..."
DB_NAME="nexusflow-db"

if doctl databases list --format "Name,ID" --no-header | grep -q "$DB_NAME"; then
    echo "✅ Database exists"
else
    echo "Creating database (this takes 3-5 minutes)..."
    doctl databases create "$DB_NAME" \
        --engine postgres \
        --version "15" \
        --region "$REGION" \
        --size "$DB_SIZE" \
        --num-nodes 1
    echo "✅ Database created"
fi

# Step 5: Get Connection String
echo ""
echo "[5/8] Getting database connection string..."
CONNECTION_STRING=$(doctl databases connection "$DB_NAME" --uri)
echo "✅ Connection string retrieved"

# Save to .env.production
cat > .env.production << EOF
DATABASE_URL=$CONNECTION_STRING
ENVIRONMENT=production
LOG_LEVEL=INFO
EOF
echo "✅ Saved to .env.production"

# Step 6: Update app.yaml
echo ""
echo "[6/8] Updating app.yaml configuration..."
if [ -f ".do/app.yaml" ]; then
    sed -i.bak "s/YOUR_GITHUB_USERNAME/${GITHUB_REPO%%\/*}/g" .do/app.yaml
    echo "✅ app.yaml updated"
else
    echo "⚠️  .do/app.yaml not found"
fi

# Step 7: Push to GitHub
echo ""
echo "[7/8] Pushing to GitHub..."
if [[ -n $(git status --porcelain) ]]; then
    echo "📝 Uncommitted changes found. Committing..."
    git add .
    git commit -m "Deploy to DigitalOcean $(date '+%Y-%m-%d %H:%M:%S')"
fi
git push origin main
echo "✅ Code pushed to GitHub"

# Step 8: Instructions
echo ""
echo "[8/8] Next steps:"
echo "📋 Manual configuration required:"
echo ""
echo "1. Go to: https://cloud.digitalocean.com/apps"
echo "2. Click 'Create App'"
echo "3. Connect GitHub repository: $GITHUB_REPO"
echo "4. Select branch: main"
echo "5. Configure environment variables:"
echo "   - OPENAI_API_KEY: sk-..."
echo "   - DATABASE_URL: \${nexusflow-db.DATABASE_URL}"
echo "   - KAFKA_BOOTSTRAP_SERVERS: your-kafka-url:9092"
echo "   - ENVIRONMENT: production"
echo "   - LOG_LEVEL: INFO"
echo "6. Click 'Create App'"
echo ""
echo "Deployment will take 5-10 minutes."
echo ""

# Summary
echo "========================================"
echo "Deployment Summary"
echo "========================================"
echo ""
echo "Project: $PROJECT_NAME"
echo "Region: $REGION"
echo "Database: $DB_NAME"
echo "App Size: $APP_SIZE (\$5/month)"
echo "Database Size: $DB_SIZE (\$15/month)"
echo ""
echo "Estimated Monthly Cost: \$20"
echo "(With \$200 free credit: FREE for 10 months!)"
echo ""
echo "📊 Monitor deployment:"
echo "   https://cloud.digitalocean.com/apps"
echo ""
echo "✅ Setup Complete!"
echo ""

# Open DigitalOcean in browser (if possible)
if command -v xdg-open &> /dev/null; then
    xdg-open "https://cloud.digitalocean.com/apps"
elif command -v open &> /dev/null; then
    open "https://cloud.digitalocean.com/apps"
fi
