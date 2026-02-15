# AWS Ubuntu Deployment Guide

## Quick Start

Deploy the Car Arbitrage scraper to an AWS Ubuntu server with web access.

**Your endpoint will be:** `http://YOUR_EC2_PUBLIC_IP/`

---

## Step 1: Launch EC2 Instance

### 1.1 Create EC2 Instance
1. Log into AWS Console → EC2
2. Click "Launch Instance"
3. **Choose:**
   - Name: `car-arbitrage-server`
   - AMI: **Ubuntu Server 22.04 LTS** (free tier eligible)
   - Instance type: **t2.micro** (free tier) or **t2.small** (recommended)
   - Key pair: Create new or use existing
   - Storage: 20 GB gp3

### 1.2 Configure Security Group
Allow these inbound rules:
- **SSH (22):** Your IP
- **HTTP (80):** 0.0.0.0/0 (Anywhere)
- **HTTPS (443):** 0.0.0.0/0 (Optional, for SSL later)

### 1.3 Launch and Note Public IP
After launch, note your **Public IPv4 address** (e.g., `3.15.123.45`)

---

## Step 2: Connect to Server

```bash
# SSH into your instance
ssh -i your-key.pem ubuntu@YOUR_EC2_PUBLIC_IP

# Example:
# ssh -i ~/.ssh/car-arbitrage.pem ubuntu@3.15.123.45
```

---

## Step 3: Install Dependencies

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python, pip, nginx
sudo apt install -y python3 python3-pip python3-venv nginx

# Install git (to clone your repo if needed)
sudo apt install -y git
```

---

## Step 4: Deploy Application

### 4.1 Create Application Directory

```bash
# Create directory
mkdir -p ~/car-arbitrage
cd ~/car-arbitrage
```

### 4.2 Upload Files

**Option A: Using SCP (from your local machine)**
```bash
# From your local machine (where the files are)
scp -i your-key.pem car_scraper.py ubuntu@YOUR_EC2_IP:~/car-arbitrage/
scp -i your-key.pem app.py ubuntu@YOUR_EC2_IP:~/car-arbitrage/
scp -i your-key.pem requirements.txt ubuntu@YOUR_EC2_IP:~/car-arbitrage/
scp -i your-key.pem car-arbitrage.service ubuntu@YOUR_EC2_IP:~/car-arbitrage/
scp -i your-key.pem nginx-site.conf ubuntu@YOUR_EC2_IP:~/car-arbitrage/
```

**Option B: Using Git**
```bash
# If you have files in a git repo
git clone YOUR_REPO_URL .
```

**Option C: Manual Copy-Paste**
```bash
# Create files manually on server
nano car_scraper.py  # Paste content
nano app.py          # Paste content
nano requirements.txt
```

### 4.3 Install Python Dependencies

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

---

## Step 5: Configure Systemd Service

```bash
# Copy service file to systemd
sudo cp car-arbitrage.service /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Enable service to start on boot
sudo systemctl enable car-arbitrage

# Start the service
sudo systemctl start car-arbitrage

# Check status
sudo systemctl status car-arbitrage
```

**Expected output:**
```
● car-arbitrage.service - Car Arbitrage Web Service
   Loaded: loaded (/etc/systemd/system/car-arbitrage.service; enabled)
   Active: active (running)
```

---

## Step 6: Configure Nginx

```bash
# Copy nginx configuration
sudo cp nginx-site.conf /etc/nginx/sites-available/car-arbitrage

# Create symlink to enable site
sudo ln -s /etc/nginx/sites-available/car-arbitrage /etc/nginx/sites-enabled/

# Remove default site
sudo rm /etc/nginx/sites-enabled/default

# Test nginx configuration
sudo nginx -t

# Restart nginx
sudo systemctl restart nginx
```

---

## Step 7: Access Your Application

### 7.1 Open in Browser
Navigate to: **`http://YOUR_EC2_PUBLIC_IP`**

Example: `http://3.15.123.45`

### 7.2 API Endpoints Available

- **Dashboard:** `http://YOUR_EC2_PUBLIC_IP/`
- **Get Deals (JSON):** `http://YOUR_EC2_PUBLIC_IP/api/deals`
- **Scraper Status:** `http://YOUR_EC2_PUBLIC_IP/api/status`
- **Get Models:** `http://YOUR_EC2_PUBLIC_IP/api/models`
- **Health Check:** `http://YOUR_EC2_PUBLIC_IP/health`

---

## Step 8: Test the Application

### 8.1 Run Demo Mode
1. Open `http://YOUR_EC2_PUBLIC_IP` in browser
2. Click "🎬 Demo Mode" button
3. Wait 2-3 seconds
4. Click "🔄 Refresh" to see sample deals

### 8.2 Run Live Scraper
1. Click "🔍 Scrape Live Data" button
2. Wait 5-15 minutes (real web scraping)
3. Deals will auto-refresh when complete

---

## Optional: Set Up Domain Name

### 8.1 Point Domain to EC2
1. In your DNS provider (Namecheap, GoDaddy, etc.)
2. Add A record: `@ → YOUR_EC2_PUBLIC_IP`
3. Add A record: `www → YOUR_EC2_PUBLIC_IP`

### 8.2 Update Nginx Config
```bash
sudo nano /etc/nginx/sites-available/car-arbitrage

# Change line:
# server_name _;
# to:
# server_name yourdomain.com www.yourdomain.com;

sudo systemctl restart nginx
```

### 8.3 Add SSL (HTTPS) with Let's Encrypt
```bash
sudo apt install -y certbot python3-certbot-nginx

sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com

# Follow prompts
# SSL will auto-renew
```

Now access: `https://yourdomain.com`

---

## Maintenance

### View Logs
```bash
# Application logs
sudo journalctl -u car-arbitrage -f

# Nginx logs
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

### Restart Service
```bash
sudo systemctl restart car-arbitrage
```

### Update Application
```bash
cd ~/car-arbitrage

# Stop service
sudo systemctl stop car-arbitrage

# Pull updates (if using git)
git pull

# Or upload new files with scp

# Install any new dependencies
source venv/bin/activate
pip install -r requirements.txt

# Start service
sudo systemctl start car-arbitrage
```

### Schedule Automatic Scraping

Add cron job to run scraper daily:
```bash
crontab -e

# Add this line to run daily at 8 AM
0 8 * * * curl -X POST http://localhost:5000/api/scrape
```

---

## Troubleshooting

### Service Won't Start
```bash
# Check logs
sudo journalctl -u car-arbitrage -n 50

# Test manually
cd ~/car-arbitrage
source venv/bin/activate
python app.py
```

### Can't Access from Browser
```bash
# Check if service is running
sudo systemctl status car-arbitrage

# Check nginx
sudo systemctl status nginx

# Check AWS Security Group allows HTTP on port 80
```

### Scraper Not Working
```bash
# Check Python dependencies
source venv/bin/activate
pip list | grep -E "(requests|beautifulsoup4|flask)"

# Test scraper directly
python car_scraper.py --demo
```

---

## Cost Estimate

**AWS Free Tier (first 12 months):**
- t2.micro instance: **FREE** (750 hours/month)
- 20 GB storage: **FREE**
- Data transfer: First 1 GB **FREE**

**After Free Tier:**
- t2.small instance: ~$17/month
- 20 GB storage: ~$2/month
- **Total: ~$19/month**

---

## Summary

✅ **Your Endpoint:** `http://YOUR_EC2_PUBLIC_IP/`

✅ **API Available:** `http://YOUR_EC2_PUBLIC_IP/api/deals`

✅ **Service:** Runs automatically on boot

✅ **Scraper:** Triggered via web interface or API

**Next Steps:**
1. Run demo mode to test
2. Try live scraping
3. Optionally add domain + SSL
4. Set up scheduled scraping with cron
