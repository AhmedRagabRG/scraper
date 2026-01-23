# ✅ تم! إضافة Category في Webhook
# ✅ Done! Category in Webhook

---

## 🎯 الميزة الجديدة / New Feature

الآن يمكنك إضافة `category` اختياري في الطلب، وسيُرسل مع كل نتيجة في الـ webhook!

Now you can add an optional `category` in your request, and it will be sent with every result in the webhook!

---

## 📝 مثال / Example

```bash
curl -X POST "http://localhost:8000/scrape" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "restaurants in Spain",
    "max_results": 50,
    "webhook_url": "YOUR_WEBHOOK_URL",
    "category": "Spanish Restaurants"
  }'
```

---

## 📊 Webhook Response

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
  }
}
```

---

## 🎯 حالات الاستخدام / Use Cases

### 1. تشغيل عدة jobs / Multiple Jobs
```bash
# مطاعم
curl -d '{"query": "restaurants", "category": "Restaurants"}'

# مقاهي
curl -d '{"query": "cafes", "category": "Cafes"}'

# فنادق
curl -d '{"query": "hotels", "category": "Hotels"}'
```

### 2. تصنيف حسب المدينة / By City
```bash
curl -d '{"query": "restaurants in Madrid", "category": "Madrid"}'
curl -d '{"query": "restaurants in Barcelona", "category": "Barcelona"}'
```

### 3. تصنيف حسب البلد / By Country
```bash
curl -d '{"query": "restaurants in Spain", "category": "Spain"}'
curl -d '{"query": "restaurants in Germany", "category": "Germany"}'
```

---

## ✅ الفوائد / Benefits

- ✅ تصنيف النتائج
- ✅ تتبع أسهل
- ✅ تنظيم أفضل
- ✅ معرفة مصدر كل نتيجة

---

**جاهز للاستخدام! / Ready to use!** 🚀

راجع `CATEGORY_FEATURE.md` لمزيد من التفاصيل  
See `CATEGORY_FEATURE.md` for more details
