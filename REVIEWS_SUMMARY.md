# 🎉 تم إضافة Reviews Scraper بنجاح!

## ✅ ما تم إنشاؤه:

### 1. **reviews_scraper.py** - Reviews Scraper كامل
- ✅ استخراج اسم المراجع
- ✅ تاريخ المراجعة
- ✅ التقييم (1-5 نجوم)
- ✅ نص المراجعة
- ✅ كشف الصور (yes/no)
- ✅ رد الشركة أو "no"

### 2. **api.py** - Endpoint جديد
- ✅ `POST /scrape-reviews`
- ✅ دعم webhook
- ✅ background processing
- ✅ job tracking

### 3. **REVIEWS_ENDPOINT_GUIDE.md** - دليل شامل
- ✅ أمثلة بكل اللغات
- ✅ حالات استخدام
- ✅ best practices

---

## 🚀 الاستخدام السريع

### Request:

```bash
curl -X POST "http://localhost:8000/scrape-reviews" \
  -H "Content-Type: application/json" \
  -d '{
    "maps_url": "https://www.google.com/maps/place/OBI/@53.6277929,14.0120623,1278m/data=!3m1!1e3!4m17!1m8!3m7!1s0x47aa4795dea1a679:0x48d36bbdbc569ea6!2sTorgelow,+Germany!3b1!8m2!3d53.6326919!4d14.0054798!16zL20vMGR5azJ6!3m7!1s0x47aa479718e3c9c5:0xe8657e96ef2b3efc!8m2!3d53.6277062!4d14.0139364!9m1!1b1!16s%2Fg%2F1tcvsx4y",
    "max_reviews": 100,
    "headless": true,
    "webhook_url": "https://n8n.tadfoq.com/webhook/your-id"
  }'
```

### Response:

```json
{
  "job_id": "abc12345",
  "status": "pending",
  "message": "Reviews scraping job started. Results will be sent to your webhook."
}
```

---

## 📊 الـ CSV Output

```csv
reviewer_name,review_date,rating,review_text,pictures,company_reply
Ahmed Mohamed,2 weeks ago,5,"Great service and friendly staff!",yes,"Thank you for your review!"
Sara Ali,1 month ago,4,"Good quality products",no,no
Mohamed Hassan,3 days ago,5,"Excellent experience",yes,"We appreciate your feedback!"
```

---

## 🔄 متابعة التقدم

```bash
# 1. فحص الحالة
curl http://localhost:8000/status/abc12345

# 2. تحميل CSV
curl http://localhost:8000/download/abc12345 -o reviews.csv

# 3. الحصول على JSON
curl http://localhost:8000/results/abc12345
```

---

## 🎯 الـ Endpoints المتاحة الآن:

| Endpoint | Description |
|----------|-------------|
| `POST /scrape` | استخراج بيانات الشركات من بحث Google Maps |
| `POST /scrape-reviews` | ✨ **جديد!** استخراج التقييمات من مكان معين |
| `GET /status/{job_id}` | فحص حالة أي job |
| `GET /download/{job_id}` | تحميل النتائج كـ CSV |
| `GET /results/{job_id}` | الحصول على النتائج كـ JSON |
| `GET /jobs` | عرض جميع الـ jobs |

---

## 🔔 مع دعم Webhook!

إذا أضفت `webhook_url`، سيتم إرسال جميع التقييمات تلقائياً عند الانتهاء:

```json
{
  "job_id": "abc12345",
  "status": "completed",
  "total_results": 100,
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

```bash
# استخدم webhook.site للاختبار
curl -X POST "http://localhost:8000/scrape-reviews" \
  -H "Content-Type: application/json" \
  -d '{
    "maps_url": "https://www.google.com/maps/place/OBI/@53.6277929,14.0120623,1278m/data=!3m1!1e3!4m17!1m8!3m7!1s0x47aa4795dea1a679:0x48d36bbdbc569ea6!2sTorgelow,+Germany!3b1!8m2!3d53.6326919!4d14.0054798!16zL20vMGR5azJ6!3m7!1s0x47aa479718e3c9c5:0xe8657e96ef2b3efc!8m2!3d53.6277062!4d14.0139364!9m1!1b1!16s%2Fg%2F1tcvsx4y",
    "max_reviews": 10,
    "webhook_url": "https://webhook.site/your-unique-id"
  }'
```

---

## ⏱️ الوقت المتوقع:

- 10 تقييمات: ~30 ثانية
- 50 تقييم: ~2 دقيقة
- 100 تقييم: ~4 دقائق
- 500+ تقييم: ~10-15 دقيقة

---

## 📚 الملفات المهمة:

1. **reviews_scraper.py** - الـ scraper
2. **api.py** - الـ API (محدّث)
3. **REVIEWS_ENDPOINT_GUIDE.md** - دليل كامل
4. **http://localhost:8000/docs** - Swagger UI

---

## 🎉 الآن جاهز للاستخدام!

الـ API يعمل على: **http://localhost:8000**

Documentation: **http://localhost:8000/docs**

---

## 💡 حالات استخدام:

### 1. تحليل آراء العملاء
```python
df = pd.read_csv('reviews.csv')
print(f"Average rating: {df['rating'].mean()}")
print(f"Reviews with pictures: {len(df[df['pictures'] == 'yes'])}")
```

### 2. مقارنة المنافسين
```python
competitors = [url1, url2, url3]
for url in competitors:
    # استخرج تقييمات كل منافس
    ...
```

### 3. مراقبة التقييمات الجديدة
```python
# استخرج آخر 20 تقييم كل 6 ساعات
schedule.every(6).hours.do(check_new_reviews)
```

---

**استمتع بالـ API الجديد! 🚀**
