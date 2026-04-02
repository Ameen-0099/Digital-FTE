# Quick Start: Deploy to DigitalOcean in 15 Minutes
# NexusFlow Customer Success Digital FTE
# ==========================================

## 🚀 Fast Track Deployment

Follow these exact steps to deploy in 15 minutes:

---

## Minute 0-2: Sign Up for DigitalOcean

1. **Go to**: https://cloud.digitalocean.com/signup
2. **Create account** (use Google/GitHub for speed)
3. **Add payment method** (required for verification)
4. **Claim $200 free credit** (automatically applied)

---

## Minute 2-5: Create PostgreSQL Database

1. **Click**: **Databases** (left sidebar)
2. **Click**: **Create Database**
3. **Configure**:
   ```
   Database Engine: PostgreSQL 15
   Plan: Basic ($15/month)
   Region: New York 3 (nyc3)
   Database Name: nexusflow
   ```
4. **Click**: **Create Database**
5. **Wait**: 3-5 minutes for provisioning
6. **Copy Connection String**:
   - Go to **Connection Details**
   - Copy the **PostgreSQL Connection String**
   - Save it (you'll need it in Minute 8)

---

## Minute 5-7: Setup Confluent Cloud (Kafka)

1. **Go to**: https://confluent.cloud/signup
2. **Sign up** with same email
3. **Create Cluster**:
   ```
   Cluster Type: Starter (Free 30 days)
   Cloud Provider: AWS
   Region: us-east-1 (closest to DO nyc3)
   ```
4. **Create API Key**:
   - Go to **API Keys**
   - Click **Create API Key**
   - **Download** the credentials
5. **Copy Bootstrap Server**:
   - Format: `pkc-xxxxx.region.provider.confluent.cloud:9092`

---

## Minute 7-10: Push Code to GitHub

```powershell
# Open PowerShell in your project folder
cd C:\Users\user\OneDrive\Desktop\hackhaton_five

# Initialize git
git init
git add .
git commit -m "Ready for DigitalOcean deployment"

# Create GitHub repo
# Go to: https://github.com/new
# Repo name: hackhaton_five
# Make it Public

# Push code
git remote add origin https://github.com/YOUR_USERNAME/hackhaton_five.git
git branch -M main
git push -u origin main
```

---

## Minute 10-13: Deploy to App Platform

1. **Go to**: https://cloud.digitalocean.com/apps
2. **Click**: **Create App**
3. **Connect GitHub**:
   - Select **GitHub**
   - Authorize DigitalOcean
   - Select your repo: `hackhaton_five`
   - Click **Next**
4. **Configure**:
   ```
   Name: nexusflow-fte
   Region: New York
   Branch: main
   Autodeploy: ✅ Enabled
   ```
5. **Add Service**:
   ```
   Source: Your GitHub repo
   Dockerfile: Dockerfile (auto-detected)
   HTTP Port: 8000
   Instance Size: Basic XXS ($5/month)
   ```
6. **Add Database**:
   ```
   Engine: PostgreSQL 15
   Plan: Basic
   Name: nexusflow-db
   ```

---

## Minute 13-15: Set Environment Variables

1. **Click**: **Edit** on environment variables
2. **Add these variables**:

```
OPENAI_API_KEY=sk-proj-YOUR_ACTUAL_KEY_HERE
DATABASE_URL=${nexusflow-db.DATABASE_URL}
KAFKA_BOOTSTRAP_SERVERS=pkc-xxxxx.region.provider.confluent.cloud:9092
KAFKA_SASL_USERNAME=YOUR_CONFLUENT_API_KEY
KAFKA_SASL_PASSWORD=YOUR_CONFLUENT_API_SECRET
ENVIRONMENT=production
LOG_LEVEL=INFO
```

3. **Click**: **Save**
4. **Click**: **Create App**

---

## ⏱️ Wait 5-10 Minutes for Deployment

**Monitor Progress**:
- **Apps** → **nexusflow-fte** → **Deployments**
- Watch the deployment progress bar

---

## ✅ Verify Deployment

### 1. Test Health Endpoint

```bash
# Get your app URL from DigitalOcean (e.g., https://nexusflow-fte-xxx.ondigitalocean.app)
curl https://your-app-url.ondigitalocean.app/health
```

**Expected Response**:
```json
{
  "status": "healthy",
  "database": "connected",
  "ai_backend": "openai"
}
```

### 2. Test Database

```bash
curl https://your-app-url.ondigitalocean.app/test-db
```

**Expected Response**:
```json
{
  "status": "success",
  "message": "Database is LIVE - 0 tickets found",
  "database": "connected"
}
```

### 3. Test Support Form

```bash
# Open in browser
https://your-app-url.ondigitalocean.app/support/form

# Submit a test ticket
```

---

## 📊 Cost Summary

| Service | Monthly Cost |
|---------|--------------|
| App Platform (Basic XXS) | $5 |
| Managed PostgreSQL (Basic) | $15 |
| Confluent Cloud (Starter) | $0 (30 days free) |
| **Total** | **$20/month** |

**With $200 free credit**: **FREE for 10 months!** 🎉

---

## 🆘 Quick Troubleshooting

### App Won't Deploy

- Check **Logs** in App Platform
- Verify `Dockerfile` exists in repo root
- Ensure port 8000 is exposed

### Database Connection Failed

- Verify connection string includes `?sslmode=require`
- Check database is in same region as app
- Ensure DATABASE_URL env var is set

### Kafka Not Connecting

- Verify bootstrap server URL is correct
- Check API key/secret are correct
- Ensure KAFKA_SASL_* variables are set

---

## 📞 Need Help?

### DigitalOcean Resources

- **Docs**: https://docs.digitalocean.com
- **Community**: https://www.digitalocean.com/community
- **Support**: Create ticket in control panel

### Project Files Reference

| File | Purpose |
|------|---------|
| `Dockerfile` | Container config |
| `.do/app.yaml` | App Platform config |
| `DIGITALOCEAN_DEPLOYMENT.md` | Full deployment guide |
| `KAFKA_SETUP.md` | Confluent Cloud setup |
| `deploy-do.ps1` | Automated deployment script |

---

## 🎉 You're Done!

Your NexusFlow Digital FTE is now:
- ✅ Running on DigitalOcean
- ✅ Connected to PostgreSQL
- ✅ Streaming to Kafka
- ✅ Ready for production use

**Live URL**: https://your-app-url.ondigitalocean.app

**Next Steps**:
1. Share with judges
2. Monitor logs for first 24 hours
3. Set up custom domain (optional)

---

**Deployment Time**: 15 minutes + 10 minutes wait = **25 minutes total** 🚀
