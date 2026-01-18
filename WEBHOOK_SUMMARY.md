# 🔔 Webhook Feature Summary

## ✅ تم إضافة ميزة Webhook!

الآن يمكنك استقبال نتائج الـ scraping تلقائياً بدون الحاجة للـ polling!

---

## 🚀 كيفية الاستخدام

### 📡 Request مع Webhook:

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

### 📦 سيتم إرسال POST request للـ webhook عند الانتهاء:

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

---

## 🧪 اختبار سريع باستخدام webhook.site

```bash
# 1. اذهب إلى https://webhook.site
# 2. انسخ الـ URL الفريد
# 3. استخدمه:

curl -X POST "http://localhost:8000/scrape" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Coffee Shops in Cairo",
    "max_results": 3,
    "webhook_url": "https://webhook.site/your-unique-id"
  }'

# 4. شاهد النتائج تصل تلقائياً على webhook.site! ✨
```

---

## 📚 الملفات المحدّثة:

1. **`api.py`**
   - ✅ إضافة `webhook_url` parameter
   - ✅ دالة `send_webhook()` لإرسال النتائج
   - ✅ إرسال تلقائي عند اكتمال الـ job
   - ✅ إرسال حتى عند الفشل

2. **`WEBHOOK_GUIDE.md`** (جديد)
   - 📖 دليل كامل للـ webhooks
   - 💻 أمثلة بكل اللغات (Python, Node.js, PHP)
   - 🧪 طرق اختبار متعددة
   - 🔐 best practices و security tips

3. **`API_EXAMPLES.md`**
   - ✅ إضافة مثال للـ webhook request

4. **`requirements.txt`**
   - ✅ إضافة `httpx` للـ HTTP requests

---

## 🎯 حالات الاستخدام:

### 1. **Automation كامل:**
```
User → API → Scraping → Webhook → Your System → Database
```

### 2. **Integration مع منصات:**
- Zapier
- Make (Integromat)
- n8n
- أي webhook receiver

### 3. **Notifications:**
- إرسال email عند الانتهاء
- Slack notification
- Discord webhook
- Telegram bot

---

## 📊 مثال Python كامل:

```python
# your_webhook_server.py
from fastapi import FastAPI, Request

app = FastAPI()

@app.post("/webhook")
async def receive_results(request: Request):
    data = await request.json()
    
    print(f"✅ Received {data['total_results']} results!")
    
    for business in data['results']:
        print(f"- {business['business_name']}: {business['rating']}⭐")
    
    # حفظ في database
    # await save_to_db(data['results'])
    
    return {"received": True}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3000)
```

---

## 🔄 Flow الكامل:

```
1. POST /scrape مع webhook_url
   ↓
2. Job يبدأ في الـ background
   ↓
3. Scraping يعمل...
   ↓
4. عند الانتهاء → POST request للـ webhook تلقائياً
   ↓
5. Webhook يستقبل النتائج ويعالجها
```

---

## 🎉 الآن جاهز للاستخدام!

شغّل الـ API:
```bash
python3 api.py
```

أو باستخدام Docker:
```bash
docker-compose up -d
```

الـ API يعمل على: `http://localhost:8000`

Documentation: `http://localhost:8000/docs`

---

للمزيد من التفاصيل، راجع:
- **WEBHOOK_GUIDE.md** - دليل شامل للـ webhooks
- **API_EXAMPLES.md** - أمثلة عملية
- **API_GUIDE.md** - دليل API الكامل
