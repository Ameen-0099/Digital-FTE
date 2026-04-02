# Confluent Cloud Kafka Setup Guide
# NexusFlow Customer Success Digital FTE
# ==========================================

## Why Confluent Cloud?

Instead of self-hosting Kafka on a DigitalOcean Droplet ($12/month), use **Confluent Cloud** for:
- ✅ **Free tier**: 30 days free, then pay-as-you-go
- ✅ **Fully managed**: No maintenance required
- ✅ **Auto-scaling**: Handles traffic spikes
- ✅ **Easy setup**: 5 minutes to configure

---

## Step 1: Sign Up for Confluent Cloud

1. **Go to**: https://confluent.cloud/signup
2. **Create account** with email or Google/GitHub
3. **Verify email**
4. **Complete onboarding** (2 minutes)

---

## Step 2: Create Kafka Cluster

1. **Get Started** → **Create Cluster**

2. **Choose Cluster Type**:
   - Select **Starter** (Free for 30 days)
   - Click **Continue**

3. **Configure Cluster**:
   - **Cluster Name**: `nexusflow-kafka`
   - **Cloud Provider**: Choose same as DigitalOcean (e.g., AWS)
   - **Region**: Choose closest to your DO region
     - If DO is `nyc3` (New York), choose `us-east-1` (AWS)
   - Click **Create Cluster**

4. **Wait for provisioning** (2-3 minutes)

---

## Step 3: Create API Credentials

1. **Go to** → **API Keys** (left sidebar)

2. **Create API Key**:
   - Click **Create API Key**
   - **Download** the credentials (save for later):
     ```
     API Key: ABCDEFGHIJKLMN
     API Secret: xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
     ```
   - **Bootstrap Server**: Copy this (format: `pkc-xxxxx.region.provider.confluent.cloud:9092`)

3. **Save credentials** in a secure location

---

## Step 4: Create Kafka Topic

1. **Go to** → **Topics** (left sidebar)

2. **Create Topic**:
   - Click **Create topic**
   - **Topic Name**: `customer-support-tickets`
   - **Partitions**: 3 (default)
   - **Replication Factor**: 2 (default)
   - Click **Create**

3. **Create Error Topic** (optional):
   - Click **Create topic**
   - **Topic Name**: `customer-support-errors`
   - Click **Create**

---

## Step 5: Update DigitalOcean Environment Variables

In DigitalOcean App Platform:

1. **Go to** → **Apps** → **nexusflow-fte** → **Settings**

2. **Edit Environment Variables**:

```bash
# Add these variables:
KAFKA_BOOTSTRAP_SERVERS=pkc-xxxxx.region.provider.confluent.cloud:9092

# For SASL authentication (if required):
KAFKA_SASL_USERNAME=YOUR_API_KEY
KAFKA_SASL_PASSWORD=YOUR_API_SECRET
KAFKA_SECURITY_PROTOCOL=SASL_SSL
```

3. **Click Save**

4. **Redeploy** app (if not automatic)

---

## Step 6: Update Your Application Code

### Option A: Environment Variables (Recommended)

Update `demo_api.py` or `production/workers/kafka_producer.py`:

```python
# Get Kafka config from environment
KAFKA_BOOTSTRAP_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS')
KAFKA_SASL_USERNAME = os.getenv('KAFKA_SASL_USERNAME')
KAFKA_SASL_PASSWORD = os.getenv('KAFKA_SASL_PASSWORD')
KAFKA_SECURITY_PROTOCOL = os.getenv('KAFKA_SECURITY_PROTOCOL', 'SASL_SSL')

# Configure producer with SSL
producer = AIOKafkaProducer(
    bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
    security_protocol=KAFKA_SECURITY_PROTOCOL,
    sasl_mechanism='PLAIN',
    sasl_plain_username=KAFKA_SASL_USERNAME,
    sasl_plain_password=KAFKA_SASL_PASSWORD,
    # ... other config
)
```

### Option B: Update kafka_producer.py

```python
# production/workers/kafka_producer.py

def __init__(
    self,
    bootstrap_servers: Optional[str] = None,
    topic: str = "customer-support-tickets",
    max_retries: int = 3,
    retry_delay: float = 1.0
):
    self.bootstrap_servers = bootstrap_servers or os.getenv(
        'KAFKA_BOOTSTRAP_SERVERS',
        'pkc-xxxxx.region.provider.confluent.cloud:9092'  # Default to Confluent
    )
    
    # Confluent Cloud requires SASL_SSL
    self.security_protocol = os.getenv('KAFKA_SECURITY_PROTOCOL', 'SASL_SSL')
    self.sasl_username = os.getenv('KAFKA_SASL_USERNAME')
    self.sasl_password = os.getenv('KAFKA_SASL_PASSWORD')
```

---

## Step 7: Test Kafka Connection

### Test from Local Machine

```bash
# Install kafka-python
pip install kafka-python

# Create test script: test_kafka.py
from kafka import KafkaProducer
import json
import os

producer = KafkaProducer(
    bootstrap_servers=[os.getenv('KAFKA_BOOTSTRAP_SERVERS')],
    security_protocol='SASL_SSL',
    sasl_mechanism='PLAIN',
    sasl_plain_username=os.getenv('KAFKA_SASL_USERNAME'),
    sasl_plain_password=os.getenv('KAFKA_SASL_PASSWORD'),
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

# Send test message
producer.send('customer-support-tickets', {'test': 'message'})
producer.flush()

print("✅ Kafka message sent successfully!")
```

```bash
# Run test
export KAFKA_BOOTSTRAP_SERVERS=pkc-xxxxx.region.provider.confluent.cloud:9092
export KAFKA_SASL_USERNAME=YOUR_API_KEY
export KAFKA_SASL_PASSWORD=YOUR_API_SECRET
python test_kafka.py
```

### Test from DigitalOcean App

```bash
# Deploy app and check logs
# In DigitalOcean Control Panel:
# Apps → nexusflow-fte → Logs

# Look for:
# "✅ Kafka producer connected"
# "📤 Event published to Kafka: TKT-xxxxx"
```

---

## Step 8: Monitor Kafka

### Confluent Cloud Dashboard

1. **Metrics**:
   - Go to **Cluster Settings** → **Metrics**
   - View throughput, latency, errors

2. **Topics**:
   - Go to **Topics** → `customer-support-tickets`
   - View message count, partitions

3. **API Keys**:
   - Go to **API Keys**
   - Rotate keys every 90 days (security best practice)

---

## 💰 Confluent Cloud Pricing

| Plan | Cost | Features |
|------|------|----------|
| **Starter** | Free (30 days) | Up to 1 GB/day, 1 topic |
| **Standard** | $0.14/GB after free tier | Unlimited topics, 99.9% SLA |
| **Dedicated** | Custom pricing | Enterprise features |

**Estimated Monthly Cost**: $0-10 (for hackathon usage)

---

## 🔧 Troubleshooting

### Connection Timeout

```bash
# Check bootstrap server format
# Should be: pkc-xxxxx.region.provider.confluent.cloud:9092

# Verify network connectivity
telnet pkc-xxxxx.region.provider.confluent.cloud 9092
```

### Authentication Failed

```bash
# Verify API key and secret
# Check for extra spaces in environment variables

# Test with kafka-console-producer
kafka-console-producer --bootstrap-server pkc-xxxxx.region.provider.confluent.cloud:9092 \
  --producer-property security.protocol=SASL_SSL \
  --producer-property sasl.mechanism=PLAIN \
  --producer-property sasl.jaas.config='org.apache.kafka.common.security.plain.PlainLoginModule required username="YOUR_KEY" password="YOUR_SECRET";' \
  --topic customer-support-tickets
```

### Topic Not Found

```bash
# Create topic in Confluent Cloud UI
# Or use CLI:
kafka-topics --create --topic customer-support-tickets \
  --bootstrap-server pkc-xxxxx.region.provider.confluent.cloud:9092 \
  --partitions 3 --replication-factor 2
```

---

## ✅ Checklist

- [ ] Confluent Cloud account created
- [ ] Kafka cluster provisioned (Starter tier)
- [ ] API credentials downloaded
- [ ] Bootstrap server URL copied
- [ ] Topic `customer-support-tickets` created
- [ ] Environment variables set in DigitalOcean
- [ ] Application code updated for SASL_SSL
- [ ] Local test successful
- [ ] DigitalOcean app logs show Kafka connected

---

## 📞 Support Resources

- **Confluent Docs**: https://docs.confluent.io/cloud/current/
- **API Reference**: https://docs.confluent.io/cloud/current/api.html
- **Support**: Available in Confluent Cloud dashboard

---

**Setup Complete! 🎉**

Your Kafka is now running on Confluent Cloud and connected to DigitalOcean!
