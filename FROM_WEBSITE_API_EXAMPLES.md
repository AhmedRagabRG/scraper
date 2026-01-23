# أمثلة استخدام API مع ميزة from_website
# API Usage Examples with from_website Feature

## 1. بدء عملية استخراج مع webhook

### مثال 1: استخراج مطاعم في القاهرة
```bash
curl -X POST "http://localhost:8000/scrape" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "restaurants in Cairo",
    "max_results": 10,
    "headless": true,
    "webhook_url": "http://localhost:8001/webhook"
  }'
```

**الاستجابة:**
```json
{
  "job_id": "abc12345",
  "status": "pending",
  "message": "Scraping job started. Use /status/abc12345 to check progress. Results will be sent to your webhook."
}
```

---

## 2. مثال على البيانات المستلمة في الـ webhook

### بيانات real-time (أثناء الاستخراج):
```json
{
  "job_id": "abc12345",
  "status": "processing",
  "current_result": 1,
  "total_expected": 10,
  "result": {
    "business_name": "مطعم الأمل",
    "rating": 4.5,
    "review_count": 120,
    "phone": "+20123456789",
    "email": "info@alamal.com",
    "from_website": true,
    "website": "https://alamal.com",
    "address": "شارع الهرم، الجيزة",
    "five_star": 80,
    "four_star": 25,
    "three_star": 10,
    "two_star": 3,
    "one_star": 2
  },
  "timestamp": "2026-01-23T17:24:28+02:00"
}
```

### مثال آخر (إيميل من Google Maps):
```json
{
  "job_id": "abc12345",
  "status": "processing",
  "current_result": 2,
  "total_expected": 10,
  "result": {
    "business_name": "مقهى النيل",
    "rating": 4.2,
    "review_count": 85,
    "phone": "+20987654321",
    "email": "nile.cafe@gmail.com",
    "from_website": false,
    "website": null,
    "address": "كورنيش النيل، القاهرة"
  },
  "timestamp": "2026-01-23T17:25:15+02:00"
}
```

### مثال ثالث (لا يوجد إيميل):
```json
{
  "job_id": "abc12345",
  "status": "processing",
  "current_result": 3,
  "total_expected": 10,
  "result": {
    "business_name": "كافيه الورد",
    "rating": 4.0,
    "review_count": 45,
    "phone": "+20555555555",
    "email": null,
    "from_website": false,
    "website": "https://alward.com",
    "address": "المعادي، القاهرة"
  },
  "timestamp": "2026-01-23T17:25:45+02:00"
}
```

---

## 3. رسالة الإتمام في الـ webhook

```json
{
  "job_id": "abc12345",
  "status": "completed",
  "total_results": 10,
  "completed_at": "2026-01-23T17:30:00+02:00",
  "download_url": "/download/abc12345",
  "message": "Scraping completed! 10 results extracted and 10 sent to webhook."
}
```

---

## 4. التحقق من حالة العملية

```bash
curl "http://localhost:8000/status/abc12345"
```

**الاستجابة:**
```json
{
  "job_id": "abc12345",
  "status": "completed",
  "query": "restaurants in Cairo",
  "progress": "Completed! 10 results (10 sent to webhook)",
  "total_results": 10,
  "created_at": "2026-01-23T17:20:00+02:00",
  "completed_at": "2026-01-23T17:30:00+02:00",
  "download_url": "/download/abc12345"
}
```

---

## 5. تحميل النتائج كـ CSV

```bash
curl "http://localhost:8000/download/abc12345" -o results.csv
```

**محتوى CSV:**
```csv
business_name,rating,review_count,five_star,four_star,three_star,two_star,one_star,phone,email,from_website,website,address
مطعم الأمل,4.5,120,80,25,10,3,2,+20123456789,info@alamal.com,true,https://alamal.com,شارع الهرم، الجيزة
مقهى النيل,4.2,85,60,15,7,2,1,+20987654321,nile.cafe@gmail.com,false,,كورنيش النيل، القاهرة
كافيه الورد,4.0,45,30,10,3,1,1,+20555555555,,false,https://alward.com,المعادي، القاهرة
```

---

## 6. الحصول على النتائج كـ JSON

```bash
curl "http://localhost:8000/results/abc12345"
```

**الاستجابة:**
```json
{
  "job_id": "abc12345",
  "total_results": 3,
  "results": [
    {
      "business_name": "مطعم الأمل",
      "rating": 4.5,
      "review_count": 120,
      "email": "info@alamal.com",
      "from_website": true,
      "website": "https://alamal.com"
    },
    {
      "business_name": "مقهى النيل",
      "rating": 4.2,
      "review_count": 85,
      "email": "nile.cafe@gmail.com",
      "from_website": false,
      "website": null
    },
    {
      "business_name": "كافيه الورد",
      "rating": 4.0,
      "review_count": 45,
      "email": null,
      "from_website": false,
      "website": "https://alward.com"
    }
  ]
}
```

---

## 7. تشغيل webhook receiver للاختبار

### الخطوة 1: تشغيل webhook receiver
```bash
python webhook_from_website_example.py
```

### الخطوة 2: في نافذة أخرى، تشغيل API
```bash
python api.py
```

### الخطوة 3: إرسال طلب استخراج
```bash
curl -X POST "http://localhost:8000/scrape" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "restaurants in Cairo",
    "max_results": 5,
    "webhook_url": "http://localhost:8001/webhook"
  }'
```

### الخطوة 4: مشاهدة النتائج في الـ webhook receiver
ستظهر النتائج في الوقت الفعلي مع حقل `from_website` في كل نتيجة!

---

## 8. فهم قيم from_website

| القيمة | المعنى | الموثوقية |
|--------|--------|-----------|
| `true` | الإيميل من الموقع الرسمي | عالية ⭐⭐⭐ |
| `false` مع إيميل | الإيميل من Google Maps | متوسطة ⭐⭐ |
| `false` بدون إيميل | لا يوجد إيميل | - |

---

## 9. تصفية النتائج حسب from_website

### في Python:
```python
import pandas as pd

# قراءة CSV
df = pd.read_csv('results.csv')

# الحصول على الإيميلات من المواقع فقط
website_emails = df[df['from_website'] == True]
print(f"Emails from websites: {len(website_emails)}")

# الحصول على الإيميلات من Google Maps فقط
maps_emails = df[(df['from_website'] == False) & (df['email'].notna())]
print(f"Emails from Google Maps: {len(maps_emails)}")

# إحصائيات
total_with_email = df['email'].notna().sum()
from_website_pct = (len(website_emails) / total_with_email * 100) if total_with_email > 0 else 0
print(f"Percentage from websites: {from_website_pct:.1f}%")
```

---

## 10. استخدام مع ngrok للاختبار العام

### الخطوة 1: تشغيل webhook receiver
```bash
python webhook_from_website_example.py
```

### الخطوة 2: تشغيل ngrok
```bash
ngrok http 8001
```

### الخطوة 3: استخدام URL من ngrok
```bash
curl -X POST "http://localhost:8000/scrape" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "restaurants in Cairo",
    "max_results": 10,
    "webhook_url": "https://your-ngrok-url.ngrok.io/webhook"
  }'
```

---

## ملاحظات مهمة

1. ✅ حقل `from_website` موجود دائماً في النتائج
2. ✅ القيمة الافتراضية هي `false`
3. ✅ تتغير إلى `true` فقط عند العثور على إيميل في الموقع الرسمي
4. ✅ يتم إرسال الحقل تلقائياً في الـ webhook
5. ✅ يظهر في ملف CSV بين `email` و `website`
