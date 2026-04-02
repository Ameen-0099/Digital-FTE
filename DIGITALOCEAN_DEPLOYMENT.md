# DigitalOcean Deployment Guide
# NexusFlow Customer Success Digital FTE
# ==========================================

## Prerequisites

1. **DigitalOcean Account**: https://cloud.digitalocean.com/signup
   - New users get $200 free credit for 60 days

2. **GitHub Account**: Your code should be pushed to GitHub

3. **OpenAI API Key**: https://platform.openai.com/api-keys

---

## Step 1: Create Managed PostgreSQL Database

### Via Control Panel:

1. Go to **Databases** → **Create Database**
2. Choose configuration:
   - **Database Engine**: PostgreSQL 15
   - **Plan**: Basic ($15/month) or Starter (free tier if available)
   - **Region**: Choose closest to you (e.g., New York 3)
   - **Database Name**: `nexusflow`
   - **Username**: `doadmin` (auto-generated)
3. Click **Create Database**
4. Wait 3-5 minutes for provisioning

### Copy Connection String:

After creation:
1. Click on your database
2. Go to **Connection Details** tab
3. Copy the **Connection String** (looks like):
   ```
   postgresql://doadmin:AVNS_password123@nexusflow-db-do-user-xxx-0.b.db.ondigitalocean.com:25060/nexusflow?sslmode=require
   ```
4. Save this for later

---

## Step 2: Setup Kafka (Choose ONE option)

### Option A: Confluent Cloud (Recommended - Free Tier)

1. **Sign up**: https://confluent.cloud/signup
2. **Create Cluster**:
   - Click **Get Started** → **Create Cluster**
   - Choose **Starter** (free for 30 days)
   - Select region (same as DigitalOcean if possible)
3. **Get Credentials**:
   - Go to **API Keys** → **Create API Key**
   - Download the credentials
4. **Copy Bootstrap Server**:
   - Format: `pkc-xxxxx.region.provider.confluent.cloud:9092`

### Option B: Self-Hosted on Droplet

1. Create Droplet: **Compute** → **Droplets**
   - Image: Ubuntu 22.04
   - Size: s-1vcpu-2gb ($12/month)
   - Region: Same as database
2. SSH into droplet and install Docker + Kafka (see KAFKA_SETUP.md)

---

## Step 3: Push Code to GitHub

```bash
# Navigate to project
cd C:\Users\user\OneDrive\Desktop\hackhaton_five

# Initialize git (if not already done)
git init
git add .
git commit -m "Ready for DigitalOcean deployment"

# Create GitHub repo and push
# Go to https://github.com/new
# Create repo named: hackhaton_five
# Then:
git remote add origin https://github.com/YOUR_USERNAME/hackhaton_five.git
git branch -M main
git push -u origin main
```

---

## Step 4: Deploy to DigitalOcean App Platform

### Via Control Panel:

1. **Go to Apps** → **Create App**
2. **Connect GitHub**:
   - Click **GitHub**
   - Authorize DigitalOcean
   - Select your repository: `hackhaton_five`
   - Click **Next**

3. **Configure App**:
   - **Name**: `nexusflow-fte`
   - **Region**: Same as your database
   - **Branch**: `main`
   - **Autodeploy**: ✅ Enabled

4. **Add Components**:
   - Click **Add Component** → **Service**
   - **Source**: Your GitHub repo
   - **Dockerfile**: `Dockerfile` (auto-detected)
   - **HTTP Port**: `8000`
   - **Instance Size**: Basic XXS ($5/month)

5. **Add Database**:
   - Click **Add Component** → **Database**
   - **Engine**: PostgreSQL 15
   - **Plan**: Basic
   - **Name**: `nexusflow-db`

6. **Set Environment Variables**:
   Click **Edit** on environment variables and add:

   ```
   OPENAI_API_KEY=sk-proj-your-actual-key-here
   DATABASE_URL=${nexusflow-db.DATABASE_URL}
   KAFKA_BOOTSTRAP_SERVERS=your-kafka-url:9092
   ENVIRONMENT=production
   LOG_LEVEL=INFO
   ```

7. **Click Create App**

### Deployment Time: 5-10 minutes

---

## Step 5: Verify Deployment

### 1. Check App Status

```bash
# In DigitalOcean Control Panel:
# Apps → nexusflow-fte → View Deployment Logs
```

### 2. Test Health Endpoint

```bash
# Get your app URL from DigitalOcean (e.g., https://nexusflow-fte-xxx.ondigitalocean.app)
curl https://your-app-url.ondigitalocean.app/health
```

**Expected Response:**
```json
{
  "status": "healthy",
  "database": "connected",
  "ai_backend": "openai"
}
```

### 3. Test Database Connection

```bash
curl https://your-app-url.ondigitalocean.app/test-db
```

**Expected Response:**
```json
{
  "status": "success",
  "message": "Database is LIVE - 0 tickets found",
  "database": "connected"
}
```

### 4. Test Support Form

```bash
curl -X POST https://your-app-url.ondigitalocean.app/support/submit \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test User",
    "email": "test@example.com",
    "subject": "Deployment Test",
    "description": "Testing DigitalOcean deployment"
  }'
```

---

## Step 6: Setup Custom Domain (Optional)

1. **Go to Apps** → **nexusflow-fte** → **Settings**
2. **Domains** → **Add Domain**
3. Enter your domain: `support.yourdomain.com`
4. **Update DNS** at your domain registrar:
   ```
   Type: CNAME
   Name: support
   Value: your-app-url.ondigitalocean.app
   ```
5. **Enable SSL**: Automatic with Let's Encrypt

---

## 🔧 Troubleshooting

### App Won't Start

```bash
# Check logs in DigitalOcean Control Panel:
# Apps → nexusflow-fte → Logs

# Common issues:
# 1. DATABASE_URL incorrect - verify connection string
# 2. OpenAI API key invalid - check key in environment
# 3. Port not 8000 - update Dockerfile EXPOSE
```

### Database Connection Failed

```bash
# 1. Verify DATABASE_URL format includes ?sslmode=require
# 2. Check database is in same region as app
# 3. Verify database allows connections from App Platform
```

### Kafka Connection Issues

```bash
# 1. Verify KAFKA_BOOTSTRAP_SERVERS is correct
# 2. For Confluent Cloud, check API keys are valid
# 3. For self-hosted, ensure firewall allows port 9092
```

---

## 💰 Cost Breakdown

| Service | Plan | Monthly Cost |
|---------|------|--------------|
| App Platform | Basic XXS | $5 |
| Managed PostgreSQL | Basic | $15 |
| Confluent Cloud | Starter | $0 (30 days free) |
| **Total** | | **$20/month** |

**With $200 free credit**: FREE for 10 months! 🎉

---

## 📊 Monitoring

### DigitalOcean Metrics

1. **Apps** → **nexusflow-fte** → **Metrics**
   - Request count
   - Response time
   - Error rate

2. **Databases** → **nexusflow-db** → **Metrics**
   - CPU usage
   - Memory usage
   - Connection count

### Setup Alerts

1. **Alerts** → **Create Alert**
2. Configure:
   - **Metric**: CPU > 80%
   - **Email**: your-email@example.com
   - **Window**: 5 minutes

---

## 🚀 Post-Deployment Tasks

### 1. Initialize Database Schema

```bash
# SSH into database or use pgAdmin
# Run: production/database/schema.sql
```

### 2. Add Sample Knowledge Base

```bash
# Insert initial knowledge base articles
# See: production/database/schema.sql for table structure
```

### 3. Test All Endpoints

```bash
# Health
curl https://your-app-url.ondigitalocean.app/health

# API Docs
open https://your-app-url.ondigitalocean.app/docs

# Support Form
open https://your-app-url.ondigitalocean.app/support/form

# Dashboard
curl https://your-app-url.ondigitalocean.app/reports/dashboard
```

### 4. Monitor First 24 Hours

- Check logs every few hours
- Monitor database connections
- Verify Kafka events are publishing
- Test support form submissions

---

## 📞 Support

### DigitalOcean Resources

- **Documentation**: https://docs.digitalocean.com
- **Community**: https://www.digitalocean.com/community
- **Support Tickets**: Available in control panel

### Project Files

- `Dockerfile` - Container configuration
- `.do/app.yaml` - App Platform configuration
- `requirements.txt` - Python dependencies
- `demo_api.py` - Main application

---

## ✅ Deployment Checklist

- [ ] DigitalOcean account created
- [ ] $200 free credit claimed
- [ ] PostgreSQL database created
- [ ] Connection string copied
- [ ] Kafka setup (Confluent or Droplet)
- [ ] Code pushed to GitHub
- [ ] App Platform app created
- [ ] Environment variables set
- [ ] Deployment successful
- [ ] Health endpoint responding
- [ ] Database connected
- [ ] Support form tested
- [ ] Custom domain configured (optional)

---

**Deployment Complete! 🎉**

Your NexusFlow Digital FTE is now live on DigitalOcean!
