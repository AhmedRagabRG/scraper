# 🚀 Docker Setup Guide

## 📦 الملفات المطلوبة

```
scraper-zac/
├── Dockerfile              ✅ جاهز
├── docker-compose.yml      ✅ جاهز
├── .dockerignore          ✅ جاهز
├── requirements.txt
├── config.py
├── scraper.py
├── main.py
├── api.py
├── reviews_scraper.py
├── google_auth.py
└── google_cookies.json    ⚠️ اختياري (مهم للـreviews!)
```

---

## 🔧 الإعداد الأولي

### 1️⃣ احفظ Google Cookies (مهم جداً!)

```bash
# على جهازك المحلي
python google_auth.py
```

هيفتح براوزر:
- سجل دخول بحساب Google
- اذهب لـGoogle Maps
- اضغط Enter
- ملف `google_cookies.json` هيتحفظ

### 2️⃣ Build الـImage

```bash
# الطريقة الأولى: Docker
docker build -t google-maps-scraper .

# الطريقة الثانية: Docker Compose (أسهل)
docker-compose build
```

---

## 🚀 التشغيل

### استخدام Docker Compose (الطريقة الموصى بها)

```bash
# Start
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down

# Restart
docker-compose restart
```

### استخدام Docker مباشرة

```bash
# Run container
docker run -d \
  --name scraper \
  -p 8000:8000 \
  -v $(pwd)/output:/app/output \
  -v $(pwd)/google_cookies.json:/app/google_cookies.json:ro \
  google-maps-scraper

# View logs
docker logs -f scraper

# Stop
docker stop scraper

# Remove
docker rm scraper
```

---

## 🔍 التحقق من التشغيل

```bash
# Check if container is running
docker ps

# Check health
curl http://localhost:8000/health

# Check API
curl http://localhost:8000/
```

Expected response:
```json
{
  "name": "Google Maps Scraper API",
  "version": "1.0.0",
  "endpoints": {...}
}
```

---

## 📤 على السيرفر

### الخطوة 1: رفع الكود

```bash
# Option 1: Git
git clone https://github.com/your-repo/scraper.git
cd scraper

# Option 2: SCP
scp -r scraper-zac/ user@server:/path/to/
```

### الخطوة 2: رفع Cookies

```bash
# من جهازك المحلي
scp google_cookies.json user@server:/path/to/scraper-zac/
```

### الخطوة 3: Build و Run

```bash
# SSH to server
ssh user@server

# Navigate to project
cd /path/to/scraper-zac

# Build and run
docker-compose up -d

# Check logs
docker-compose logs -f
```

---

## 🔄 التحديث

```bash
# Pull latest code
git pull

# Rebuild and restart
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

---

## 📊 Monitoring

### View Logs
```bash
# All logs
docker-compose logs -f

# Last 100 lines
docker-compose logs --tail=100

# Specific service
docker-compose logs -f scraper
```

### Container Stats
```bash
# Resource usage
docker stats

# Inspect container
docker inspect google-maps-scraper
```

---

## 🐛 Troubleshooting

### Problem: Container won't start
```bash
# Check logs
docker-compose logs

# Rebuild
docker-compose build --no-cache
docker-compose up -d
```

### Problem: "No cookies found"
```bash
# Verify cookies file exists
ls -la google_cookies.json

# Copy cookies to container
docker cp google_cookies.json google-maps-scraper:/app/

# Restart
docker-compose restart
```

### Problem: Port 8000 already in use
```bash
# Find process using port
lsof -i :8000

# Kill it
kill -9 <PID>

# Or change port in docker-compose.yml
ports:
  - "8001:8000"
```

### Problem: Xvfb not working
```bash
# Check if Xvfb is running
docker exec google-maps-scraper ps aux | grep Xvfb

# Manual test
docker exec -it google-maps-scraper bash
Xvfb :99 -screen 0 1920x1080x24 &
export DISPLAY=:99
python api.py
```

---

## 🔐 Security Notes

- ⚠️ `google_cookies.json` contains sensitive data
- ✅ Added to `.gitignore`
- ✅ Mounted as read-only (`:ro`) in Docker
- 🔒 Keep it secure!

---

## 📝 Environment Variables

Create `.env` file (optional):
```bash
PORT=8000
USE_PROXIES=false
HEADLESS=false
```

Update `docker-compose.yml`:
```yaml
env_file:
  - .env
```

---

## 🎯 Production Tips

1. **Use Docker Volumes** for persistent data
2. **Enable Logging** to file
3. **Set Resource Limits**:
```yaml
deploy:
  resources:
    limits:
      cpus: '2'
      memory: 4G
```

4. **Use Reverse Proxy** (Nginx):
```nginx
location /scraper/ {
    proxy_pass http://localhost:8000/;
}
```

---

## ✅ Success Checklist

- [ ] `google_cookies.json` exists
- [ ] Docker image built successfully
- [ ] Container running (`docker ps`)
- [ ] Health check passes
- [ ] API responds at http://localhost:8000
- [ ] Reviews scraper works with authentication

---

## 🎉 Ready to Use!

```bash
curl -X POST "http://localhost:8000/scrape-reviews" \
  -H "Content-Type: application/json" \
  -d '{
    "maps_url": "https://www.google.com/maps/place/...",
    "max_reviews": 100,
    "headless": true,
    "webhook_url": "https://your-webhook.com"
  }'
```
