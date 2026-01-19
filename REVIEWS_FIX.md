# 🔧 Reviews Scraper - التحسينات والإصلاحات

## ❌ المشكلة السابقة:
- الـ scraper كان ينقر على Reviews tab لكن لا يجد التقييمات (0 reviews)
- الـ selectors القديمة لا تعمل مع هيكل Google Maps الجديد

## ✅ ما تم إصلاحه:

### 1. **Multiple Selectors لكل عنصر**
بدلاً من selector واحد، الآن يجرب عدة selectors حتى يجد التقييمات:

#### للتقييمات (Reviews):
```python
review_selectors = [
    'div[data-review-id]',      # الأساسي
    'div.jftiEf',                # بديل 1
    'div[jsaction*="review"]',   # بديل 2
]
```

#### لاسم المراجع:
```python
name_selectors = [
    'div[class*="d4r55"]',
    'button[aria-label]',
    'a[aria-label]',
    'div.WNxzHc span',
]
```

#### لتاريخ المراجعة:
```python
date_selectors = [
    'span[class*="rsqaWe"]',
    'span.DU9Pgb',
    'span[aria-label]',
]
```

#### لنص المراجعة:
```python
text_selectors = [
    'span[class*="wiI7pd"]',
    'span[jsan*="review"]',
    'div.MyEned span',
    'span.Ahvqpe',
]
```

### 2. **Improved Scrolling**
- ✅ انتظار أطول بعد النقر على Reviews tab (3 ثوانٍ)
- ✅ محاولة selectors متعددة قبل الفشل
- ✅ Fallback scrolling للـ feed إذا لم تُكتشف التقييمات
- ✅ وقت انتظار أطول بين scrolls (2-3 ثوانٍ)

### 3. **Better Detection للصور**
```python
image_selectors = [
    'button[aria-label*="photo"]',
    'button[jsaction*="photo"]',
    'img[src*="googleusercontent"]',
    'button.Tya61d',
]
```

### 4. **Improved Company Reply Detection**
- ✅ selectors متعددة
- ✅ فحص محتوى النص للتأكد أنه رد فعلي
- ✅ البحث عن كلمات مفتاحية: "response", "owner"

### 5. **Better Error Handling**
- ✅ رسائل واضحة عند فشل كل selector
- ✅ fallback mechanisms
- ✅ logging محسّن

---

## 🧪 اختبار التحديثات:

```bash
curl -X POST "http://localhost:8000/scrape-reviews" \
  -H "Content-Type: application/json" \
  -d '{
    "maps_url": "https://www.google.com/maps/place/OBI/@53.6277929,14.0120623,1278m/data=!3m1!1e3!4m17!1m8!3m7!1s0x47aa4795dea1a679:0x48d36bbdbc569ea6!2sTorgelow,+Germany!3b1!8m2!3d53.6326919!4d14.0054798!16zL20vMGR5azJ6!3m7!1s0x47aa479718e3c9c5:0xe8657e96ef2b3efc!8m2!3d53.6277062!4d14.0139364!9m1!1b1!16s%2Fg%2F1tcvsx4y",
    "max_reviews": 20,
    "headless": false
  }'
```

---

## 📊 النتائج المتوقعة:

بدلاً من:
```
Loaded 0 reviews...
✓ Successfully extracted 0 reviews
```

الآن:
```
✓ Found reviews using selector: div.jftiEf
Loaded 50 reviews...
✓ Successfully extracted 50 reviews
```

---

## 🔍 Debugging Tips:

### 1. تشغيل بدون headless للمشاهدة:
```bash
curl -X POST "http://localhost:8000/scrape-reviews" \
  -H "Content-Type: application/json" \
  -d '{
    "maps_url": "YOUR_URL",
    "max_reviews": 10,
    "headless": false  
  }'
```

### 2. فحص الـ logs:
```bash
# شاهد logs الـ API
tail -f /Users/ahmed/.cursor/projects/Users-ahmed-Desktop-programing-work/terminals/15.txt
```

### 3. اختبار URL معين:
تأكد أن الـ URL:
- ✅ يحتوي على `/place/` في المسار
- ✅ مكان له تقييمات فعلاً
- ✅ URL كامل (مع جميع الـ parameters)

---

## 💡 ملاحظات:

### إذا استمرت المشكلة:

1. **جرّب بدون headless:**
   ```json
   {"headless": false}
   ```

2. **جرّب مكان آخر:**
   - بعض الأماكن قد لا يكون لها reviews tab
   - جرّب مكان مشهور بتقييمات كثيرة

3. **تحقق من الـ URL:**
   ```python
   # URL صحيح
   https://www.google.com/maps/place/NAME/@LAT,LONG,ZOOM/data=...
   
   # URL خاطئ
   https://www.google.com/maps/search/...
   ```

4. **فحص الـ consent dialog:**
   - قد يحتاج المتصفح للموافقة على cookies
   - الـ scraper يحاول الموافقة تلقائياً

---

## ✅ الآن جاهز!

التحديثات تم تطبيقها. جرّب الآن! 🚀

```bash
# اختبار سريع
curl -X POST "http://localhost:8000/scrape-reviews" \
  -H "Content-Type: application/json" \
  -d '{
    "maps_url": "https://www.google.com/maps/place/...",
    "max_reviews": 10
  }'
```
