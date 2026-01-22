# ميزة إرسال النتائج للـ Webhook في الوقت الفعلي (Real-time)
**التاريخ:** 2026-01-22

## الميزة الجديدة
دلوقتي لما تضيف webhook URL، الـ API هيبعت كل result لحظة ما تخلص بدل ما ينتظر كل النتائج تخلص ويبعتهم مرة واحدة.

## الفوائد
1. **تحديثات فورية** - تقدر تشوف النتائج وهي بتتجمع live
2. **تجربة أفضل** - المستخدم مش محتاج ينتظر لحد ما كل الـ scraping يخلص
3. **معالجة أسرع** - تقدر تبدأ تعالج النتائج قبل ما الـ job يخلص
4. **شفافية أكتر** - تعرف بالظبط قد إيه اتجمع من النتائج

## كيفية الاستخدام

### 1. إرسال طلب Scraping مع Webhook
```bash
curl -X POST "http://localhost:8000/scrape" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "مطاعم في القاهرة",
    "max_results": 10,
    "webhook_url": "https://your-webhook-url.com/endpoint"
  }'
```

### 2. استقبال النتائج في الوقت الفعلي

#### أ) رسائل النتائج الفردية (لكل result)
كل ما result واحدة تخلص، هتستقبل:
```json
{
  "job_id": "abc123",
  "status": "processing",
  "current_result": 3,
  "total_expected": 10,
  "result": {
    "business_name": "مطعم أحمد",
    "rating": 4.5,
    "review_count": 120,
    "phone": "+20123456789",
    "website": "https://example.com",
    "address": "القاهرة، مصر",
    "email": "info@example.com",
    "one_star": 5,
    "two_star": 10,
    "three_star": 15,
    "four_star": 30,
    "five_star": 60
  },
  "timestamp": "2026-01-22T13:53:21+02:00"
}
```

**الحقول:**
- `job_id`: معرف الـ job
- `status`: "processing" (الـ scraping لسه شغال)
- `current_result`: رقم الـ result الحالية (مثلاً 3 من 10)
- `total_expected`: العدد المتوقع من النتائج
- `result`: بيانات المطعم/المكان الكاملة
- `timestamp`: وقت استخراج الـ result

#### ب) رسالة الإكمال النهائية
لما الـ scraping يخلص تماماً، هتستقبل:
```json
{
  "job_id": "abc123",
  "status": "completed",
  "total_results": 10,
  "completed_at": "2026-01-22T14:00:00+02:00",
  "download_url": "/download/abc123",
  "message": "Scraping completed! 10 results extracted and 10 sent to webhook."
}
```

**الحقول:**
- `status`: "completed" (الـ job خلص)
- `total_results`: إجمالي النتائج المستخرجة
- `completed_at`: وقت الإكمال
- `download_url`: رابط تحميل ملف CSV
- `message`: رسالة توضيحية

#### ج) رسالة الخطأ (في حالة فشل الـ scraping)
```json
{
  "job_id": "abc123",
  "status": "failed",
  "error": "وصف الخطأ",
  "completed_at": "2026-01-22T14:00:00+02:00"
}
```

## مثال: Webhook Receiver بسيط (Python)

```python
from fastapi import FastAPI, Request
import json

app = FastAPI()

# تخزين النتائج
results = {}

@app.post("/webhook")
async def receive_webhook(request: Request):
    data = await request.json()
    
    job_id = data.get("job_id")
    status = data.get("status")
    
    if status == "processing":
        # نتيجة جديدة
        current = data.get("current_result")
        total = data.get("total_expected")
        result = data.get("result")
        
        print(f"📥 Received result {current}/{total} for job {job_id}")
        print(f"   Business: {result.get('business_name')}")
        
        # حفظ النتيجة
        if job_id not in results:
            results[job_id] = []
        results[job_id].append(result)
        
    elif status == "completed":
        # الـ job خلص
        total = data.get("total_results")
        print(f"✅ Job {job_id} completed! Total: {total} results")
        
    elif status == "failed":
        # الـ job فشل
        error = data.get("error")
        print(f"❌ Job {job_id} failed: {error}")
    
    return {"status": "received"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
```

## مثال: Webhook Receiver (Node.js/Express)

```javascript
const express = require('express');
const app = express();

app.use(express.json());

// تخزين النتائج
const results = {};

app.post('/webhook', (req, res) => {
    const { job_id, status, current_result, total_expected, result } = req.body;
    
    if (status === 'processing') {
        // نتيجة جديدة
        console.log(`📥 Received result ${current_result}/${total_expected} for job ${job_id}`);
        console.log(`   Business: ${result.business_name}`);
        
        // حفظ النتيجة
        if (!results[job_id]) {
            results[job_id] = [];
        }
        results[job_id].push(result);
        
    } else if (status === 'completed') {
        // الـ job خلص
        console.log(`✅ Job ${job_id} completed! Total: ${req.body.total_results} results`);
        
    } else if (status === 'failed') {
        // الـ job فشل
        console.log(`❌ Job ${job_id} failed: ${req.body.error}`);
    }
    
    res.json({ status: 'received' });
});

app.listen(8001, () => {
    console.log('Webhook receiver running on port 8001');
});
```

## الفرق بين النظام القديم والجديد

### النظام القديم ❌
```
[بدء الـ scraping] → ... انتظار ... → [كل النتائج خلصت] → [إرسال webhook واحد بكل النتائج]
```
- المستخدم ينتظر لحد ما كل شيء يخلص
- لو في 100 result، هتنتظر كلهم يخلصوا
- webhook واحد فقط في النهاية

### النظام الجديد ✅
```
[بدء الـ scraping] 
  → [Result 1 خلصت] → [إرسال webhook]
  → [Result 2 خلصت] → [إرسال webhook]
  → [Result 3 خلصت] → [إرسال webhook]
  → ...
  → [كل النتائج خلصت] → [إرسال webhook نهائي]
```
- المستخدم يشوف النتائج live
- كل result تظهر فوراً
- webhooks متعددة + webhook نهائي

## ملاحظات مهمة

1. **Timeout الـ Webhook**: كل webhook فردي عنده timeout 10 ثواني، والـ webhook النهائي عنده 30 ثانية

2. **معالجة الأخطاء**: لو webhook فردي فشل، الـ scraping هيكمل عادي ومش هيتوقف

3. **الترتيب**: النتائج هتوصل بنفس ترتيب استخراجها من Google Maps

4. **الأداء**: الـ webhooks بتتبعت بشكل async فمش هتأثر على سرعة الـ scraping

5. **CSV File**: في النهاية، كل النتائج كمان هتتحفظ في ملف CSV تقدر تحمله

## اختبار الميزة

### استخدام webhook.site للاختبار السريع
1. روح على https://webhook.site
2. هتلاقي URL فريد (مثلاً: https://webhook.site/abc-123)
3. استخدم الـ URL ده في طلب الـ scraping
4. شوف النتائج وهي بتوصل live على الموقع

### مثال:
```bash
curl -X POST "http://localhost:8000/scrape" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "مطاعم في القاهرة",
    "max_results": 5,
    "webhook_url": "https://webhook.site/YOUR-UNIQUE-ID"
  }'
```

## الملفات المعدلة
- ✏️ `scraper.py` - إضافة `on_result_callback` parameter
- ✏️ `api.py` - تعديل `run_scraper` لاستخدام الـ callback وإرسال webhooks فورية
- 📄 `REALTIME_WEBHOOK_AR.md` - هذا الملف (التوثيق)

## الدعم الفني
لو عندك أي مشاكل أو أسئلة:
1. تأكد إن الـ webhook URL شغال ويقبل POST requests
2. شوف الـ logs في console الـ API
3. استخدم webhook.site للاختبار أولاً
