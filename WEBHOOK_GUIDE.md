# 🔔 Webhook Integration Guide

## نظرة عامة

الآن يمكنك استقبال نتائج الـ scraping تلقائياً عن طريق Webhook! عند انتهاء عملية الـ scraping، سيتم إرسال POST request تلقائياً إلى الـ URL الذي تحدده.

---

## 📡 كيفية الاستخدام

### 1️⃣ إرسال Request مع Webhook URL

```bash
curl -X POST "http://localhost:8000/scrape" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Coffee Shops in Cairo",
    "max_results": 10,
    "headless": true,
    "webhook_url": "https://your-server.com/webhook"
  }'
```

### Response:

```json
{
  "job_id": "a1b2c3d4",
  "status": "pending",
  "message": "Scraping job started. Results will be sent to your webhook."
}
```

---

## 📦 Webhook Payload Structure

عند اكتمال الـ scraping، سيتم إرسال POST request إلى webhook_url مع البيانات التالية:

### ✅ عند النجاح:

```json
{
  "job_id": "a1b2c3d4",
  "status": "completed",
  "total_results": 10,
  "completed_at": "2026-01-17T12:34:56",
  "results": [
    {
      "business_name": "Great Coffee Shop",
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

### ❌ عند الفشل:

```json
{
  "job_id": "a1b2c3d4",
  "status": "failed",
  "error": "Error message here",
  "completed_at": "2026-01-17T12:34:56"
}
```

---

## 🎯 إنشاء Webhook Endpoint

### مثال 1: Node.js/Express

```javascript
const express = require('express');
const app = express();

app.use(express.json());

app.post('/webhook', (req, res) => {
  const { job_id, status, total_results, results } = req.body;
  
  console.log(`Received webhook for job: ${job_id}`);
  console.log(`Status: ${status}`);
  console.log(`Total results: ${total_results}`);
  
  if (status === 'completed') {
    // معالجة النتائج
    results.forEach(business => {
      console.log(`- ${business.business_name}: ${business.rating}⭐`);
    });
    
    // حفظ في قاعدة البيانات
    // await saveToDatabase(results);
  }
  
  // يجب إرجاع 200 لتأكيد الاستلام
  res.status(200).json({ received: true });
});

app.listen(3000, () => {
  console.log('Webhook server running on port 3000');
});
```

---

### مثال 2: Python/Flask

```python
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    
    job_id = data.get('job_id')
    status = data.get('status')
    total_results = data.get('total_results')
    results = data.get('results', [])
    
    print(f"Received webhook for job: {job_id}")
    print(f"Status: {status}")
    print(f"Total results: {total_results}")
    
    if status == 'completed':
        # معالجة النتائج
        for business in results:
            print(f"- {business['business_name']}: {business['rating']}⭐")
        
        # حفظ في قاعدة البيانات
        # save_to_database(results)
    
    # يجب إرجاع 200 لتأكيد الاستلام
    return jsonify({'received': True}), 200

if __name__ == '__main__':
    app.run(port=3000)
```

---

### مثال 3: Python/FastAPI

```python
from fastapi import FastAPI, Request
from typing import List, Dict, Optional

app = FastAPI()

class WebhookPayload:
    job_id: str
    status: str
    total_results: Optional[int]
    completed_at: str
    results: Optional[List[Dict]]
    error: Optional[str]

@app.post("/webhook")
async def receive_webhook(request: Request):
    data = await request.json()
    
    job_id = data.get('job_id')
    status = data.get('status')
    
    print(f"📥 Received webhook for job: {job_id}")
    print(f"📊 Status: {status}")
    
    if status == 'completed':
        results = data.get('results', [])
        print(f"✅ Received {len(results)} results")
        
        # معالجة النتائج
        for business in results:
            print(f"  - {business['business_name']}: {business.get('rating')}⭐")
        
        # حفظ في قاعدة البيانات
        # await save_to_database(results)
        
    elif status == 'failed':
        error = data.get('error')
        print(f"❌ Job failed: {error}")
    
    return {"received": True}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3000)
```

---

### مثال 4: PHP

```php
<?php
// webhook.php

// قراءة البيانات
$json = file_get_contents('php://input');
$data = json_decode($json, true);

$jobId = $data['job_id'] ?? '';
$status = $data['status'] ?? '';
$totalResults = $data['total_results'] ?? 0;
$results = $data['results'] ?? [];

// تسجيل
error_log("Received webhook for job: $jobId");
error_log("Status: $status");

if ($status === 'completed') {
    error_log("Total results: $totalResults");
    
    // معالجة النتائج
    foreach ($results as $business) {
        $name = $business['business_name'];
        $rating = $business['rating'];
        error_log("- $name: $rating⭐");
    }
    
    // حفظ في قاعدة البيانات
    // saveToDatabase($results);
}

// إرجاع 200
http_response_code(200);
header('Content-Type: application/json');
echo json_encode(['received' => true]);
?>
```

---

## 🧪 اختبار الـ Webhook محلياً

### استخدام webhook.site (الأسهل)

1. اذهب إلى [webhook.site](https://webhook.site)
2. انسخ الـ URL الفريد
3. استخدمه في الـ request:

```bash
curl -X POST "http://localhost:8000/scrape" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Coffee Shops in Cairo",
    "max_results": 5,
    "webhook_url": "https://webhook.site/your-unique-id"
  }'
```

4. شاهد النتائج على webhook.site تلقائياً! ✨

---

### استخدام ngrok (لاختبار webhook محلي)

```bash
# 1. شغّل webhook server محلي (port 3000)
python your_webhook_server.py

# 2. في terminal آخر، شغّل ngrok
ngrok http 3000

# 3. انسخ الـ URL (مثل: https://abc123.ngrok.io)

# 4. استخدمه في الـ request
curl -X POST "http://localhost:8000/scrape" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Coffee Shops in Cairo",
    "max_results": 5,
    "webhook_url": "https://abc123.ngrok.io/webhook"
  }'
```

---

## 🔐 أمان الـ Webhook

### 1. التحقق من الـ Source

```python
# أضف secret token
WEBHOOK_SECRET = "your-secret-token"

@app.post("/webhook")
async def receive_webhook(request: Request):
    # تحقق من الـ token في الـ header
    token = request.headers.get('X-Webhook-Secret')
    if token != WEBHOOK_SECRET:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    # معالجة الـ webhook
    data = await request.json()
    # ...
```

### 2. تحديد IP المسموح

```python
ALLOWED_IPS = ['your-scraper-server-ip']

@app.post("/webhook")
async def receive_webhook(request: Request):
    client_ip = request.client.host
    if client_ip not in ALLOWED_IPS:
        raise HTTPException(status_code=403, detail="Forbidden")
    
    # معالجة الـ webhook
    # ...
```

---

## 📝 Best Practices

### 1. ✅ استجب بـ 200 دائماً

```python
# Good
return {"received": True}, 200

# Bad - يسبب retry غير ضروري
return {"error": "something"}, 500
```

### 2. ⚡ معالجة سريعة

```python
@app.post("/webhook")
async def receive_webhook(request: Request):
    data = await request.json()
    
    # ✅ حفظ سريع
    await queue.put(data)
    
    # ✅ إرجاع فوري
    return {"received": True}

# ❌ لا تعمل معالجة طويلة هنا
# await process_all_data(data)  # سيستغرق وقتاً طويلاً
```

### 3. 💾 حفظ البيانات

```python
import json
from datetime import datetime

@app.post("/webhook")
async def receive_webhook(request: Request):
    data = await request.json()
    
    # حفظ نسخة احتياطية
    filename = f"webhook_{data['job_id']}_{datetime.now().timestamp()}.json"
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)
    
    return {"received": True}
```

### 4. 🔄 إعادة المحاولة عند الفشل

```python
# في الـ scraper API
max_retries = 3
for attempt in range(max_retries):
    try:
        response = await client.post(webhook_url, json=payload)
        if response.status_code == 200:
            break
    except:
        if attempt == max_retries - 1:
            # log failure
            pass
        await asyncio.sleep(2 ** attempt)  # exponential backoff
```

---

## 🌐 منصات Webhook جاهزة

### Zapier
```
https://hooks.zapier.com/hooks/catch/xxxxx/yyyyy/
```

### Make (Integromat)
```
https://hook.us1.make.com/xxxxxxxxxxxxx
```

### n8n
```
https://your-n8n-instance.com/webhook/xxxxxxxxxxxxx
```

---

## 📊 مثال كامل: حفظ في MongoDB

```python
from fastapi import FastAPI
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime

app = FastAPI()

# اتصال MongoDB
client = AsyncIOMotorClient("mongodb://localhost:27017")
db = client.scraper_db
collection = db.results

@app.post("/webhook")
async def receive_webhook(request: Request):
    data = await request.json()
    
    if data['status'] == 'completed':
        # تحضير البيانات
        for business in data['results']:
            business['job_id'] = data['job_id']
            business['scraped_at'] = datetime.now()
            
            # حفظ في MongoDB
            await collection.insert_one(business)
        
        print(f"✅ Saved {len(data['results'])} businesses to MongoDB")
    
    return {"received": True}
```

---

## 🎉 الآن جاهز!

الآن لديك:
- ✅ Webhook integration كامل
- ✅ استقبال تلقائي للنتائج
- ✅ أمثلة بكل اللغات
- ✅ Best practices

استمتع بالـ automation! 🚀
