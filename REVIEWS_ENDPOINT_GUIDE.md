# 📝 Google Maps Reviews Scraper Endpoint

## نظرة عامة

Endpoint جديد لاستخراج التقييمات (reviews) من أي مكان على Google Maps!

---

## 🚀 الاستخدام

### Endpoint:
```
POST /scrape-reviews
```

### Request Body:

```json
{
  "maps_url": "https://www.google.com/maps/place/...",
  "max_reviews": 50,
  "headless": true,
  "webhook_url": "https://your-webhook.com/endpoint"  // اختياري
}
```

---

## 📡 مثال cURL

```bash
curl -X POST "http://localhost:8000/scrape-reviews" \
  -H "Content-Type: application/json" \
  -d '{
    "maps_url": "https://www.google.com/maps/place/OBI/@53.6277929,14.0120623,1278m/data=!3m1!1e3!4m17!1m8!3m7!1s0x47aa4795dea1a679:0x48d36bbdbc569ea6!2sTorgelow,+Germany!3b1!8m2!3d53.6326919!4d14.0054798!16zL20vMGR5azJ6!3m7!1s0x47aa479718e3c9c5:0xe8657e96ef2b3efc!8m2!3d53.6277062!4d14.0139364!9m1!1b1!16s%2Fg%2F1tcvsx4y",
    "max_reviews": 100,
    "headless": true
  }'
```

### Response:

```json
{
  "job_id": "abc12345",
  "status": "pending",
  "message": "Reviews scraping job started. Use /status/abc12345 to check progress."
}
```

---

## 📊 البيانات المستخرجة

الـ CSV سيحتوي على الأعمدة التالية:

| Column | Description | Example |
|--------|-------------|---------|
| `reviewer_name` | اسم المراجع | "Ahmed Mohamed" |
| `review_date` | تاريخ المراجعة | "2 weeks ago" |
| `rating` | التقييم (1-5 نجوم) | 5 |
| `review_text` | نص المراجعة | "Great service!" |
| `pictures` | هل يوجد صور؟ | "yes" أو "no" |
| `company_reply` | رد الشركة | "Thank you!" أو "no" |

### مثال CSV Output:

```csv
reviewer_name,review_date,rating,review_text,pictures,company_reply
Ahmed Mohamed,2 weeks ago,5,"Great service and friendly staff!",yes,"Thank you for your review!"
Sara Ali,1 month ago,4,"Good quality products",no,no
Mohamed Hassan,3 days ago,5,"Excellent experience",yes,"We appreciate your feedback!"
```

---

## 🔄 متابعة التقدم

### 1. فحص حالة الـ Job

```bash
curl http://localhost:8000/status/abc12345
```

### Response:

```json
{
  "job_id": "abc12345",
  "status": "running",
  "type": "reviews",
  "maps_url": "https://www.google.com/maps/...",
  "progress": "Loaded 50 reviews...",
  "total_results": null,
  "created_at": "2026-01-17T12:00:00"
}
```

### 2. تحميل النتائج

```bash
# تحميل CSV
curl http://localhost:8000/download/abc12345 -o reviews.csv

# أو الحصول على JSON
curl http://localhost:8000/results/abc12345
```

---

## 🔔 استخدام Webhook

إذا أضفت `webhook_url`، سيتم إرسال النتائج تلقائياً عند الانتهاء:

```bash
curl -X POST "http://localhost:8000/scrape-reviews" \
  -H "Content-Type: application/json" \
  -d '{
    "maps_url": "https://www.google.com/maps/place/...",
    "max_reviews": 50,
    "webhook_url": "https://n8n.tadfoq.com/webhook/your-id"
  }'
```

### Webhook Payload:

```json
{
  "job_id": "abc12345",
  "status": "completed",
  "total_results": 50,
  "completed_at": "2026-01-17T12:05:00",
  "results": [
    {
      "reviewer_name": "Ahmed Mohamed",
      "review_date": "2 weeks ago",
      "rating": 5,
      "review_text": "Great service!",
      "pictures": "yes",
      "company_reply": "Thank you!"
    },
    ...
  ]
}
```

---

## 🧪 اختبار سريع

### 1. باستخدام webhook.site

```bash
# 1. اذهب إلى https://webhook.site
# 2. انسخ URL الفريد
# 3. استخدمه:

curl -X POST "http://localhost:8000/scrape-reviews" \
  -H "Content-Type: application/json" \
  -d '{
    "maps_url": "https://www.google.com/maps/place/...",
    "max_reviews": 10,
    "webhook_url": "https://webhook.site/your-unique-id"
  }'
```

---

## 💻 أمثلة بلغات مختلفة

### Python

```python
import requests

# Start scraping
response = requests.post('http://localhost:8000/scrape-reviews', json={
    'maps_url': 'https://www.google.com/maps/place/OBI/@53.6277929,14.0120623...',
    'max_reviews': 100,
    'headless': True,
    'webhook_url': 'https://your-webhook.com/endpoint'
})

job_id = response.json()['job_id']
print(f"Job started: {job_id}")

# Wait and download
import time
while True:
    status = requests.get(f'http://localhost:8000/status/{job_id}').json()
    print(f"Status: {status['status']} - {status.get('progress', '')}")
    
    if status['status'] == 'completed':
        # Download CSV
        with open('reviews.csv', 'wb') as f:
            csv_data = requests.get(f'http://localhost:8000/download/{job_id}')
            f.write(csv_data.content)
        print("✅ Reviews downloaded!")
        break
    
    time.sleep(5)
```

---

### JavaScript/Node.js

```javascript
const axios = require('axios');

async function scrapeReviews() {
  // Start scraping
  const response = await axios.post('http://localhost:8000/scrape-reviews', {
    maps_url: 'https://www.google.com/maps/place/...',
    max_reviews: 100,
    headless: true,
    webhook_url: 'https://your-webhook.com/endpoint'
  });
  
  const jobId = response.data.job_id;
  console.log(`Job started: ${jobId}`);
  
  // Wait for completion
  while (true) {
    const status = await axios.get(`http://localhost:8000/status/${jobId}`);
    console.log(`Status: ${status.data.status} - ${status.data.progress || ''}`);
    
    if (status.data.status === 'completed') {
      // Download results
      const results = await axios.get(`http://localhost:8000/results/${jobId}`);
      console.log(`✅ Downloaded ${results.data.total_results} reviews!`);
      break;
    }
    
    await new Promise(resolve => setTimeout(resolve, 5000));
  }
}

scrapeReviews();
```

---

## ⚙️ Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `maps_url` | string | ✅ Yes | - | URL الكامل للمكان على Google Maps |
| `max_reviews` | integer | ❌ No | null | الحد الأقصى للتقييمات (null = كل التقييمات) |
| `headless` | boolean | ❌ No | true | تشغيل المتصفح بدون واجهة |
| `webhook_url` | string | ❌ No | null | URL لإرسال النتائج تلقائياً |

---

## 📝 ملاحظات مهمة

### 1. كيفية الحصول على Google Maps URL:

1. افتح Google Maps
2. ابحث عن المكان
3. انقر على المكان لفتح صفحته
4. انسخ الـ URL من شريط العناوين

**مثال URL صحيح:**
```
https://www.google.com/maps/place/OBI/@53.6277929,14.0120623,1278m/data=!3m1!1e3!4m17...
```

### 2. الوقت المتوقع:

- 10 تقييمات: ~30 ثانية
- 50 تقييم: ~2 دقيقة
- 100 تقييم: ~4 دقائق
- 500+ تقييم: ~10-15 دقيقة

### 3. معلومات التقييمات:

- **reviewer_name**: اسم المراجع كما يظهر في Google
- **review_date**: التاريخ النسبي (e.g., "2 weeks ago", "1 month ago")
- **rating**: رقم من 1 إلى 5
- **review_text**: النص الكامل للمراجعة
- **pictures**: "yes" إذا كان التقييم يحتوي على صور، "no" غير ذلك
- **company_reply**: نص رد الشركة، أو "no" إذا لم يكن هناك رد

---

## 🔥 حالات استخدام

### 1. تحليل آراء العملاء
```python
import pandas as pd

df = pd.read_csv('reviews.csv')

# متوسط التقييمات
print(f"Average rating: {df['rating'].mean()}")

# عدد التقييمات مع صور
with_pics = len(df[df['pictures'] == 'yes'])
print(f"Reviews with pictures: {with_pics}")

# عدد ردود الشركة
with_reply = len(df[df['company_reply'] != 'no'])
print(f"Company replied to: {with_reply} reviews")
```

### 2. مقارنة المنافسين
```python
# استخرج تقييمات لعدة أماكن
competitors = [
    'https://www.google.com/maps/place/competitor1/...',
    'https://www.google.com/maps/place/competitor2/...',
    'https://www.google.com/maps/place/competitor3/...'
]

for url in competitors:
    response = requests.post('http://localhost:8000/scrape-reviews', json={
        'maps_url': url,
        'max_reviews': 100
    })
    print(f"Started job: {response.json()['job_id']}")
```

### 3. مراقبة التقييمات الجديدة
```python
# استخرج التقييمات دورياً وقارنها
import schedule
import time

def check_new_reviews():
    response = requests.post('http://localhost:8000/scrape-reviews', json={
        'maps_url': 'your-place-url',
        'max_reviews': 20,  # آخر 20 تقييم
        'webhook_url': 'https://your-notification-webhook.com'
    })
    print(f"Checking for new reviews: {response.json()['job_id']}")

# كل 6 ساعات
schedule.every(6).hours.do(check_new_reviews)

while True:
    schedule.run_pending()
    time.sleep(60)
```

---

## 🎉 جاهز!

الآن يمكنك استخراج تقييمات Google Maps بسهولة! 🚀

للمزيد:
- **API Documentation**: http://localhost:8000/docs
- **Webhook Guide**: WEBHOOK_GUIDE.md
- **API Examples**: API_EXAMPLES.md
