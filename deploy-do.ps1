# Deployment Scripts for DigitalOcean
# NexusFlow Customer Success Digital FTE
# ==========================================

# =============================================================================
# WINDOWS POWERSHELL SCRIPT
# =============================================================================

<#
.SYNOPSIS
    Deploy NexusFlow Digital FTE to DigitalOcean App Platform

.DESCRIPTION
    This script automates the deployment process to DigitalOcean.

.NOTES
    Prerequisites:
    - doctl (DigitalOcean CLI) installed
    - GitHub CLI (gh) installed (optional)
    - Git installed
    
    Install doctl:
    winget install DigitalOcean.doctl
#>

# Configuration
$PROJECT_NAME = "nexusflow-fte"
$GITHUB_REPO = "YOUR_GITHUB_USERNAME/hackhaton_five"
$REGION = "nyc"  # New York
$APP_SIZE = "basic-xxs"
$DB_SIZE = "db-s-dev-database"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "NexusFlow Digital FTE - DO Deployment" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Check doctl installation
Write-Host "[1/8] Checking doctl installation..." -ForegroundColor Yellow
try {
    $doctlVersion = doctl version
    Write-Host "✅ doctl installed: $doctlVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ doctl not found. Install with: winget install DigitalOcean.doctl" -ForegroundColor Red
    exit 1
}

# Step 2: Authenticate with DigitalOcean
Write-Host ""
Write-Host "[2/8] Authenticating with DigitalOcean..." -ForegroundColor Yellow
Write-Host "📋 Get your API token from: https://cloud.digitalocean.com/api"
$token = Read-Host "Enter your DigitalOcean API token"
$env:DIGITALOCEAN_ACCESS_TOKEN = $token

try {
    doctl auth init -t $token | Out-Null
    Write-Host "✅ Authentication successful" -ForegroundColor Green
} catch {
    Write-Host "❌ Authentication failed. Check your token." -ForegroundColor Red
    exit 1
}

# Step 3: Create Project (if not exists)
Write-Host ""
Write-Host "[3/8] Setting up project..." -ForegroundColor Yellow
try {
    $project = doctl projects list --format "Name,ID" --no-header | Select-String -Pattern $PROJECT_NAME
    if ($project) {
        Write-Host "✅ Project exists" -ForegroundColor Green
    } else {
        doctl projects create --name $PROJECT_NAME --purpose "web-application" --environment Development | Out-Null
        Write-Host "✅ Project created" -ForegroundColor Green
    }
} catch {
    Write-Host "⚠️  Could not create project. Continuing..." -ForegroundColor Yellow
}

# Step 4: Create Managed Database
Write-Host ""
Write-Host "[4/8] Creating Managed PostgreSQL Database..." -ForegroundColor Yellow
$DB_NAME = "nexusflow-db"

try {
    $db = doctl databases list --format "Name,ID" --no-header | Select-String -Pattern $DB_NAME
    if ($db) {
        Write-Host "✅ Database exists" -ForegroundColor Green
    } else {
        Write-Host "Creating database (this takes 3-5 minutes)..." -ForegroundColor Cyan
        doctl databases create $DB_NAME `
            --engine postgres `
            --version "15" `
            --region $REGION `
            --size $DB_SIZE `
            --num-nodes 1 | Out-Null
        
        Write-Host "✅ Database created" -ForegroundColor Green
    }
} catch {
    Write-Host "⚠️  Database creation may be in progress. Check DO control panel." -ForegroundColor Yellow
}

# Step 5: Get Database Connection String
Write-Host ""
Write-Host "[5/8] Getting database connection string..." -ForegroundColor Yellow

try {
    $connectionString = doctl databases connection $DB_NAME --uri
    Write-Host "✅ Connection string retrieved" -ForegroundColor Green
    
    # Save to .env.production
    $envContent = @"
DATABASE_URL=$connectionString
ENVIRONMENT=production
LOG_LEVEL=INFO
"@
    $envContent | Out-File -FilePath ".env.production" -Encoding utf8
    Write-Host "✅ Saved to .env.production" -ForegroundColor Green
} catch {
    Write-Host "⚠️  Could not get connection string. Get it from DO control panel." -ForegroundColor Yellow
}

# Step 6: Update app.yaml
Write-Host ""
Write-Host "[6/8] Updating app.yaml configuration..." -ForegroundColor Yellow

$appYamlPath = ".do\app.yaml"
if (Test-Path $appYamlPath) {
    $content = Get-Content $appYamlPath -Raw
    $content = $content -replace "YOUR_GITHUB_USERNAME", $GITHUB_REPO.Split("/")[0]
    $content | Set-Content $appYamlPath
    Write-Host "✅ app.yaml updated" -ForegroundColor Green
} else {
    Write-Host "⚠️  .do\app.yaml not found. Create it manually." -ForegroundColor Yellow
}

# Step 7: Push to GitHub
Write-Host ""
Write-Host "[7/8] Pushing to GitHub..." -ForegroundColor Yellow

try {
    $gitStatus = git status --porcelain
    if ($gitStatus) {
        Write-Host "📝 Uncommitted changes found. Committing..." -ForegroundColor Cyan
        git add .
        git commit -m "Deploy to DigitalOcean $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
    }
    
    git push origin main
    Write-Host "✅ Code pushed to GitHub" -ForegroundColor Green
} catch {
    Write-Host "❌ Git push failed. Check your repository setup." -ForegroundColor Red
    Write-Host "   Manual steps:" -ForegroundColor Yellow
    Write-Host "   1. git add ." -ForegroundColor Yellow
    Write-Host "   2. git commit -m 'Deploy to DO'" -ForegroundColor Yellow
    Write-Host "   3. git push origin main" -ForegroundColor Yellow
}

# Step 8: Create App Platform App
Write-Host ""
Write-Host "[8/8] Creating App Platform application..." -ForegroundColor Yellow
Write-Host "📋 Next steps:" -ForegroundColor Cyan
Write-Host ""
Write-Host "1. Go to: https://cloud.digitalocean.com/apps" -ForegroundColor White
Write-Host "2. Click 'Create App'" -ForegroundColor White
Write-Host "3. Connect GitHub repository: $GITHUB_REPO" -ForegroundColor White
Write-Host "4. Select branch: main" -ForegroundColor White
Write-Host "5. Configure environment variables:" -ForegroundColor White
Write-Host "   - OPENAI_API_KEY: sk-..." -ForegroundColor Yellow
Write-Host "   - DATABASE_URL: \${nexusflow-db.DATABASE_URL}" -ForegroundColor Yellow
Write-Host "   - KAFKA_BOOTSTRAP_SERVERS: your-kafka-url:9092" -ForegroundColor Yellow
Write-Host "   - ENVIRONMENT: production" -ForegroundColor Yellow
Write-Host "   - LOG_LEVEL: INFO" -ForegroundColor Yellow
Write-Host "6. Click 'Create App'" -ForegroundColor White
Write-Host ""
Write-Host "Deployment will take 5-10 minutes." -ForegroundColor Cyan
Write-Host ""

# Show summary
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Deployment Summary" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Project: $PROJECT_NAME" -ForegroundColor White
Write-Host "Region: $REGION" -ForegroundColor White
Write-Host "Database: $DB_NAME" -ForegroundColor White
Write-Host "App Size: $APP_SIZE (`$5/month)" -ForegroundColor White
Write-Host "Database Size: $DB_SIZE (`$15/month)" -ForegroundColor White
Write-Host ""
Write-Host "Estimated Monthly Cost: `$20" -ForegroundColor Green
Write-Host "(With `$200 free credit: FREE for 10 months!)" -ForegroundColor Green
Write-Host ""
Write-Host "📊 Monitor deployment:" -ForegroundColor Cyan
Write-Host "   https://cloud.digitalocean.com/apps" -ForegroundColor White
Write-Host ""
Write-Host "✅ Setup Complete!" -ForegroundColor Green
Write-Host ""

# Open DigitalOcean in browser
Start-Process "https://cloud.digitalocean.com/apps"
