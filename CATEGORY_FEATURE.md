# ميزة Category في Webhook
# Category Feature in Webhook

## التاريخ / Date: 2026-01-23

---

## 🇪🇬 بالعربية

### ✅ الميزة الجديدة

الآن يمكنك إضافة حقل `category` اختياري في طلب الاستخراج، وسيتم إرساله مع كل نتيجة في الـ webhook!

### 🎯 الفائدة

- ✅ تصنيف النتائج حسب الفئة
- ✅ معرفة مصدر كل نتيجة في الـ webhook
- ✅ تنظيم البيانات بشكل أفضل
- ✅ سهولة التتبع عند تشغيل عدة jobs

---

## 📝 كيفية الاستخدام

### مثال 1: مطاعم في إسبانيا
```bash
curl -X POST "http://localhost:8000/scrape" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "restaurants in Spain",
    "max_results": 50,
    "webhook_url": "https://your-webhook.com/endpoint",
    "category": "Spanish Restaurants"
  }'
```

### مثال 2: مقاهي في ألمانيا
```bash
curl -X POST "http://localhost:8000/scrape" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "cafes in Germany",
    "max_results": 30,
    "webhook_url": "https://your-webhook.com/endpoint",
    "category": "German Cafes"
  }'
```

### مثال 3: فنادق في فرنسا
```bash
curl -X POST "http://localhost:8000/scrape" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "hotels in Paris",
    "max_results": 20,
    "webhook_url": "https://your-webhook.com/endpoint",
    "category": "Paris Hotels"
  }'
```

---

## 📊 شكل البيانات في Webhook

### بدون category (قديم):
```json
{
  "job_id": "abc123",
  "status": "processing",
  "current_result": 1,
  "total_expected": 50,
  "result": {
    "business_name": "Restaurante El Sol",
    "email": "info@elsol.es",
    "from_website": true
  },
  "timestamp": "2026-01-23T17:48:00+02:00"
}
```

### مع category (جديد):
```json
{
  "job_id": "abc123",
  "status": "processing",
  "current_result": 1,
  "total_expected": 50,
  "category": "Spanish Restaurants",
  "result": {
    "business_name": "Restaurante El Sol",
    "email": "info@elsol.es",
    "from_website": true
  },
  "timestamp": "2026-01-23T17:48:00+02:00"
}
```

---

## 🎯 حالات الاستخدام

### 1. تشغيل عدة jobs في نفس الوقت
```bash
# Job 1: مطاعم
curl -X POST "http://localhost:8000/scrape" \
  -d '{"query": "restaurants in Madrid", "category": "Restaurants"}'

# Job 2: مقاهي
curl -X POST "http://localhost:8000/scrape" \
  -d '{"query": "cafes in Madrid", "category": "Cafes"}'

# Job 3: فنادق
curl -X POST "http://localhost:8000/scrape" \
  -d '{"query": "hotels in Madrid", "category": "Hotels"}'
```

في الـ webhook، يمكنك التمييز بين النتائج حسب `category`!

### 2. تصنيف حسب المدينة
```bash
# مدريد
curl -X POST "http://localhost:8000/scrape" \
  -d '{"query": "restaurants in Madrid", "category": "Madrid"}'

# برشلونة
curl -X POST "http://localhost:8000/scrape" \
  -d '{"query": "restaurants in Barcelona", "category": "Barcelona"}'
```

### 3. تصنيف حسب البلد
```bash
# إسبانيا
curl -X POST "http://localhost:8000/scrape" \
  -d '{"query": "restaurants in Spain", "category": "Spain"}'

# ألمانيا
curl -X POST "http://localhost:8000/scrape" \
  -d '{"query": "restaurants in Germany", "category": "Germany"}'
```

---

## 🔍 في Webhook Receiver

يمكنك الآن تصفية وتنظيم النتائج حسب `category`:

```python
@app.post("/webhook")
async def receive_webhook(request: Request):
    data = await request.json()
    
    # الحصول على category
    category = data.get('category', 'Unknown')
    result = data.get('result', {})
    
    print(f"📦 Category: {category}")
    print(f"🏢 Business: {result.get('business_name')}")
    
    # حفظ في قاعدة بيانات مع category
    save_to_database(result, category)
    
    return {"status": "received"}
```

---

## 📈 مثال: تنظيم البيانات

### في قاعدة البيانات:
```
| business_name      | email           | category            |
|--------------------|-----------------|---------------------|
| Restaurante El Sol | info@elsol.es   | Spanish Restaurants |
| Café Berlin        | info@berlin.de  | German Cafes        |
| Hotel Paris        | info@paris.fr   | Paris Hotels        |
```

### في Excel/CSV:
```csv
business_name,email,category,from_website
Restaurante El Sol,info@elsol.es,Spanish Restaurants,true
Café Berlin,info@berlin.de,German Cafes,true
Hotel Paris,info@paris.fr,Paris Hotels,false
```

---

## ⚙️ التفاصيل التقنية

### الحقل اختياري:
- ✅ إذا لم تحدد `category`، لن يظهر في الـ webhook
- ✅ إذا حددت `category`، سيظهر في كل webhook response

### أين يظهر:
- ✅ في كل webhook request (real-time)
- ✅ في job info عند `/status/{job_id}`
- ❌ لا يظهر في ملف CSV (فقط في webhook)

---

## 🇬🇧 In English

### ✅ New Feature

You can now add an optional `category` field in your scraping request, and it will be sent with every result in the webhook!

### 🎯 Benefits

- ✅ Classify results by category
- ✅ Know the source of each result in webhook
- ✅ Better data organization
- ✅ Easy tracking when running multiple jobs

---

## 📝 Usage Examples

### Example 1: Restaurants in Spain
```bash
curl -X POST "http://localhost:8000/scrape" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "restaurants in Spain",
    "max_results": 50,
    "webhook_url": "https://your-webhook.com/endpoint",
    "category": "Spanish Restaurants"
  }'
```

### Example 2: Multiple Jobs
```bash
# Job 1: Restaurants
curl -X POST "http://localhost:8000/scrape" \
  -d '{"query": "restaurants in Madrid", "category": "Restaurants"}'

# Job 2: Cafes
curl -X POST "http://localhost:8000/scrape" \
  -d '{"query": "cafes in Madrid", "category": "Cafes"}'
```

---

## 📊 Webhook Response Format

```json
{
  "job_id": "abc123",
  "status": "processing",
  "current_result": 1,
  "total_expected": 50,
  "category": "Spanish Restaurants",
  "result": {
    "business_name": "Restaurante El Sol",
    "email": "info@elsol.es",
    "from_website": true
  },
  "timestamp": "2026-01-23T17:48:00+02:00"
}
```

---

## ✅ Summary

| Feature | Before | After |
|---------|--------|-------|
| Category in request | ❌ | ✅ |
| Category in webhook | ❌ | ✅ |
| Easy classification | ❌ | ✅ |
| Multiple jobs tracking | Hard | Easy |

---

**جاهز للاستخدام! / Ready to use!** 🚀
