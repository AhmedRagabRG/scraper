# تحديث: إضافة حقل from_website

## التاريخ: 2026-01-23

## الوصف
تم إضافة حقل جديد `from_website` في البيانات المستخرجة من Google Maps Scraper لتتبع مصدر الإيميل.

## التفاصيل

### الحقل الجديد: `from_website`
- **النوع**: Boolean (true/false)
- **الوصف**: يحدد ما إذا كان الإيميل مستخرج من الموقع الرسمي للشركة أم من Google Maps مباشرة

### القيم الممكنة:
- `true`: الإيميل تم استخراجه من الموقع الرسمي للشركة
- `false`: الإيميل تم استخراجه من Google Maps مباشرة (أو لم يتم العثور على إيميل)

## الاستخدام

### في ملف CSV
سيظهر الحقل `from_website` في ملف CSV بين عمود `email` وعمود `website`:

```
business_name,rating,review_count,...,email,from_website,website,address
مطعم الأمل,4.5,120,...,info@alamal.com,true,https://alamal.com,القاهرة
مقهى النيل,4.2,85,...,nile@gmail.com,false,,الجيزة
```

### في Webhook
عند إرسال البيانات عبر الـ webhook، سيتم تضمين حقل `from_website` في كل نتيجة:

```json
{
  "job_id": "abc123",
  "status": "processing",
  "current_result": 1,
  "total_expected": 10,
  "result": {
    "business_name": "مطعم الأمل",
    "rating": 4.5,
    "review_count": 120,
    "email": "info@alamal.com",
    "from_website": true,
    "website": "https://alamal.com",
    "phone": "+20123456789",
    "address": "القاهرة"
  },
  "timestamp": "2026-01-23T17:24:28+02:00"
}
```

## آلية العمل

1. **الأولوية الأولى**: إذا كان للشركة موقع إلكتروني:
   - يتم زيارة الموقع واستخراج الإيميل منه
   - إذا تم العثور على إيميل: `from_website = true`

2. **الأولوية الثانية**: إذا لم يتم العثور على إيميل في الموقع:
   - يتم البحث عن الإيميل في صفحة Google Maps
   - إذا تم العثور على إيميل: `from_website = false`

3. **لا يوجد إيميل**:
   - إذا لم يتم العثور على إيميل: `email = null` و `from_website = false`

## الملفات المعدلة

1. **scraper.py**:
   - إضافة حقل `from_website` في `_extract_place_details()`
   - تحديث المنطق لتعيين `true` عند استخراج الإيميل من الموقع
   - تحديث المنطق لتعيين `false` عند استخراج الإيميل من Google Maps

2. **api.py**:
   - إضافة `from_website` في ترتيب أعمدة CSV

## مثال عملي

### طلب API:
```bash
curl -X POST "http://localhost:8000/scrape" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "مطاعم في القاهرة",
    "max_results": 5,
    "webhook_url": "https://your-webhook.com/endpoint"
  }'
```

### النتيجة في Webhook:
```json
{
  "job_id": "abc123",
  "status": "processing",
  "current_result": 1,
  "total_expected": 5,
  "result": {
    "business_name": "مطعم الأمل",
    "email": "info@alamal.com",
    "from_website": true,
    "website": "https://alamal.com"
  }
}
```

## الفوائد

1. **شفافية البيانات**: معرفة مصدر الإيميل يساعد في تقييم جودة البيانات
2. **التحقق من الصحة**: الإيميلات من المواقع الرسمية عادة أكثر موثوقية
3. **التحليل**: يمكن تحليل نسبة الشركات التي لديها إيميلات على مواقعها الرسمية
