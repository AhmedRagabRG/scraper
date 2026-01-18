# 🗺️ Google Maps Scraper API

API لاستخراج بيانات الشركات من Google Maps عن طريق HTTP requests

## 🚀 التشغيل المحلي (Local)

### 1. تثبيت المتطلبات

```bash
pip install -r requirements.txt
playwright install chromium
```

### 2. تشغيل API Server

```bash
python api.py
```

أو باستخدام uvicorn مباشرة:

```bash
uvicorn api:app --host 0.0.0.0 --port 8000 --reload
```

الـ API سيعمل على: `http://localhost:8000`

---

## 🐳 التشغيل باستخدام Docker

### طريقة 1: Docker Build & Run

```bash
# بناء الـ image
docker build -t google-maps-scraper .

# تشغيل الـ container
docker run -d \
  --name scraper-api \
  -p 8000:8000 \
  -v $(pwd)/output:/app/output \
  google-maps-scraper
```

### طريقة 2: Docker Compose (الأسهل)

```bash
# تشغيل
docker-compose up -d

# إيقاف
docker-compose down

# عرض logs
docker-compose logs -f
```

---

## 📡 API Endpoints

### 1️⃣ **GET /** - معلومات الـ API

```bash
curl http://localhost:8000/
```

Response:
```json
{
  "name": "Google Maps Scraper API",
  "version": "1.0.0",
  "endpoints": {...}
}
```

---

### 2️⃣ **POST /scrape** - بدء عملية Scraping

#### Request:

```bash
curl -X POST "http://localhost:8000/scrape" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Coffee Shops in Cairo",
    "max_results": 10,
    "headless": true
  }'
```

#### Response:

```json
{
  "job_id": "a1b2c3d4",
  "status": "pending",
  "message": "Scraping job started. Use /status/a1b2c3d4 to check progress."
}
```

---

### 3️⃣ **GET /status/{job_id}** - متابعة حالة الـ Job

```bash
curl http://localhost:8000/status/a1b2c3d4
```

#### Response (Running):

```json
{
  "job_id": "a1b2c3d4",
  "status": "running",
  "query": "Coffee Shops in Cairo",
  "progress": "Processing 5/10...",
  "created_at": "2026-01-17T12:00:00"
}
```

#### Response (Completed):

```json
{
  "job_id": "a1b2c3d4",
  "status": "completed",
  "query": "Coffee Shops in Cairo",
  "total_results": 10,
  "created_at": "2026-01-17T12:00:00",
  "completed_at": "2026-01-17T12:05:00",
  "download_url": "/download/a1b2c3d4"
}
```

---

### 4️⃣ **GET /download/{job_id}** - تحميل CSV

```bash
curl http://localhost:8000/download/a1b2c3d4 -o results.csv
```

أو عن طريق المتصفح:
```
http://localhost:8000/download/a1b2c3d4
```

---

### 5️⃣ **GET /results/{job_id}** - الحصول على JSON

```bash
curl http://localhost:8000/results/a1b2c3d4
```

#### Response:

```json
{
  "job_id": "a1b2c3d4",
  "total_results": 10,
  "results": [
    {
      "business_name": "Coffee Shop",
      "rating": 4.5,
      "review_count": 250,
      "five_star": 180,
      "four_star": 50,
      "three_star": 15,
      "two_star": 3,
      "one_star": 2,
      "phone": "+20123456789",
      "email": "info@coffee.com",
      "website": "https://coffee.com",
      "address": "Cairo, Egypt"
    },
    ...
  ]
}
```

---

### 6️⃣ **GET /jobs** - عرض جميع الـ Jobs

```bash
curl http://localhost:8000/jobs
```

---

### 7️⃣ **DELETE /job/{job_id}** - حذف Job

```bash
curl -X DELETE http://localhost:8000/job/a1b2c3d4
```

---

### 8️⃣ **GET /health** - Health Check

```bash
curl http://localhost:8000/health
```

---

## 📝 أمثلة عملية

### مثال 1: Scraping بسيط

```bash
# 1. ابدأ الـ job
RESPONSE=$(curl -s -X POST "http://localhost:8000/scrape" \
  -H "Content-Type: application/json" \
  -d '{"query": "Restaurants in Cairo", "max_results": 20}')

# 2. استخرج job_id
JOB_ID=$(echo $RESPONSE | grep -o '"job_id":"[^"]*' | cut -d'"' -f4)

echo "Job ID: $JOB_ID"

# 3. انتظر حتى ينتهي
while true; do
  STATUS=$(curl -s "http://localhost:8000/status/$JOB_ID" | grep -o '"status":"[^"]*' | cut -d'"' -f4)
  echo "Status: $STATUS"
  
  if [ "$STATUS" = "completed" ] || [ "$STATUS" = "failed" ]; then
    break
  fi
  
  sleep 5
done

# 4. حمّل النتائج
curl "http://localhost:8000/download/$JOB_ID" -o results.csv
echo "Results saved to results.csv"
```

---

### مثال 2: باستخدام Python

```python
import requests
import time

# 1. ابدأ الـ scraping
response = requests.post('http://localhost:8000/scrape', json={
    'query': 'Coffee Shops in Cairo',
    'max_results': 10,
    'headless': True
})

job_id = response.json()['job_id']
print(f"Job started: {job_id}")

# 2. انتظر حتى ينتهي
while True:
    status = requests.get(f'http://localhost:8000/status/{job_id}').json()
    print(f"Status: {status['status']} - {status.get('progress', '')}")
    
    if status['status'] in ['completed', 'failed']:
        break
    
    time.sleep(5)

# 3. احصل على النتائج كـ JSON
if status['status'] == 'completed':
    results = requests.get(f'http://localhost:8000/results/{job_id}').json()
    print(f"Total results: {results['total_results']}")
    
    # أو حمّل CSV
    with open('results.csv', 'wb') as f:
        csv_data = requests.get(f'http://localhost:8000/download/{job_id}')
        f.write(csv_data.content)
    print("CSV downloaded!")
```

---

### مثال 3: باستخدام JavaScript/Node.js

```javascript
const axios = require('axios');
const fs = require('fs');

async function scrapeGoogleMaps() {
  // 1. ابدأ الـ scraping
  const response = await axios.post('http://localhost:8000/scrape', {
    query: 'Hotels in Cairo',
    max_results: 15,
    headless: true
  });
  
  const jobId = response.data.job_id;
  console.log(`Job started: ${jobId}`);
  
  // 2. انتظر حتى ينتهي
  let status;
  while (true) {
    const statusRes = await axios.get(`http://localhost:8000/status/${jobId}`);
    status = statusRes.data;
    console.log(`Status: ${status.status} - ${status.progress || ''}`);
    
    if (status.status === 'completed' || status.status === 'failed') {
      break;
    }
    
    await new Promise(resolve => setTimeout(resolve, 5000));
  }
  
  // 3. حمّل النتائج
  if (status.status === 'completed') {
    const results = await axios.get(`http://localhost:8000/results/${jobId}`);
    console.log(`Total results: ${results.data.total_results}`);
    
    // حفظ CSV
    const csv = await axios.get(`http://localhost:8000/download/${jobId}`, {
      responseType: 'stream'
    });
    csv.data.pipe(fs.createWriteStream('results.csv'));
    console.log('CSV downloaded!');
  }
}

scrapeGoogleMaps();
```

---

## 🌐 النشر على السيرفر

### الطريقة 1: على VPS مباشرة

```bash
# 1. انسخ الملفات للسيرفر
scp -r . user@your-server:/path/to/app

# 2. على السيرفر
cd /path/to/app
docker-compose up -d

# 3. افتح Port 8000 في الـ firewall
sudo ufw allow 8000
```

---

### الطريقة 2: على Railway

```bash
# 1. أنشئ حساب على Railway.app
# 2. نصّب Railway CLI
npm install -g @railway/cli

# 3. Login
railway login

# 4. أنشئ project
railway init

# 5. Deploy
railway up
```

أضف `railway.json`:
```json
{
  "build": {
    "builder": "DOCKERFILE"
  },
  "deploy": {
    "startCommand": "python api.py",
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
  }
}
```

---

### الطريقة 3: على Render

1. اذهب إلى [render.com](https://render.com)
2. اربط GitHub repo
3. اختر "Docker"
4. Deploy!

---

## 🔧 Environment Variables

```bash
PORT=8000                    # API port
PYTHONUNBUFFERED=1          # Python output buffering
```

---

## 📊 البيانات المستخرجة

| Field | Description |
|-------|-------------|
| `business_name` | اسم الشركة |
| `rating` | التقييم (1-5) |
| `review_count` | عدد التقييمات |
| `five_star` | عدد تقييمات 5 نجوم |
| `four_star` | عدد تقييمات 4 نجوم |
| `three_star` | عدد تقييمات 3 نجوم |
| `two_star` | عدد تقييمات نجمتين |
| `one_star` | عدد تقييمات نجمة واحدة |
| `phone` | رقم الهاتف |
| `email` | البريد الإلكتروني |
| `website` | الموقع الإلكتروني |
| `address` | العنوان |

---

## 🛠️ Troubleshooting

### المشكلة: Browser لا يفتح

**الحل:**
```bash
playwright install chromium
playwright install-deps chromium
```

### المشكلة: Port مشغول

**الحل:**
```bash
# غيّر الـ port
PORT=8080 python api.py
```

### المشكلة: Timeout errors

**الحل:**
قلل `max_results` أو شغّل بدون headless للتصحيح.

---

## 📚 Swagger Docs

افتح في المتصفح:
```
http://localhost:8000/docs
```

للحصول على واجهة Swagger تفاعلية! 🎯

---

## 🎉 Done!

الآن لديك API كامل جاهز للاستخدام! 🚀
