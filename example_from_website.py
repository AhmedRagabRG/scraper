#!/usr/bin/env python3
"""
مثال بسيط لاستخدام ميزة from_website
Simple example demonstrating the from_website feature
"""

import asyncio
import json
from scraper import scrape_google_maps


async def example_usage():
    """مثال على استخدام الميزة الجديدة"""
    
    print("=" * 80)
    print("مثال: استخراج بيانات مع تتبع مصدر الإيميل")
    print("Example: Scraping with email source tracking")
    print("=" * 80)
    print()
    
    # استخراج 5 نتائج
    print("🔍 البحث عن: مطاعم في القاهرة")
    print("🔍 Searching for: restaurants in Cairo")
    print()
    
    results = await scrape_google_maps(
        search_term="restaurants in Cairo",
        headless=True,
        max_results=5
    )
    
    print("\n" + "=" * 80)
    print(f"📊 النتائج: {len(results)} مطعم")
    print(f"📊 Results: {len(results)} restaurants")
    print("=" * 80)
    print()
    
    # عرض النتائج
    for idx, result in enumerate(results, 1):
        print(f"\n{idx}. {result.get('business_name', 'N/A')}")
        print(f"   {'─' * 70}")
        
        # الإيميل ومصدره
        email = result.get('email')
        from_website = result.get('from_website')
        website = result.get('website')
        
        if email:
            source = "🌐 الموقع الرسمي" if from_website else "🗺️  Google Maps"
            source_en = "🌐 Official Website" if from_website else "🗺️  Google Maps"
            print(f"   📧 الإيميل: {email}")
            print(f"   📧 Email: {email}")
            print(f"   📍 المصدر: {source} / {source_en}")
        else:
            print(f"   📧 الإيميل: غير متوفر / Not available")
        
        if website:
            print(f"   🌐 الموقع: {website}")
            print(f"   🌐 Website: {website}")
        
        # معلومات إضافية
        if result.get('phone'):
            print(f"   📞 الهاتف: {result.get('phone')}")
            print(f"   📞 Phone: {result.get('phone')}")
        
        if result.get('rating'):
            print(f"   ⭐ التقييم: {result.get('rating')}")
            print(f"   ⭐ Rating: {result.get('rating')}")
    
    # إحصائيات
    print("\n" + "=" * 80)
    print("📈 الإحصائيات / Statistics")
    print("=" * 80)
    
    total = len(results)
    with_email = [r for r in results if r.get('email')]
    from_website_list = [r for r in with_email if r.get('from_website') == True]
    from_maps_list = [r for r in with_email if r.get('from_website') == False]
    
    print(f"\n   إجمالي النتائج / Total results: {total}")
    print(f"   مع إيميل / With email: {len(with_email)} ({len(with_email)/total*100:.1f}%)")
    
    if with_email:
        print(f"\n   مصادر الإيميلات / Email sources:")
        print(f"   ├─ من المواقع / From websites: {len(from_website_list)} ({len(from_website_list)/len(with_email)*100:.1f}%)")
        print(f"   └─ من Google Maps: {len(from_maps_list)} ({len(from_maps_list)/len(with_email)*100:.1f}%)")
    
    # حفظ النتائج
    print("\n" + "=" * 80)
    print("💾 حفظ النتائج / Saving results")
    print("=" * 80)
    
    output_file = "example_output.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"\n   ✅ تم الحفظ في: {output_file}")
    print(f"   ✅ Saved to: {output_file}")
    
    # عرض مثال JSON
    if results:
        print("\n" + "=" * 80)
        print("📄 مثال JSON / JSON Example")
        print("=" * 80)
        print()
        print(json.dumps(results[0], ensure_ascii=False, indent=2))
    
    print("\n" + "=" * 80)
    print("✅ انتهى المثال / Example completed")
    print("=" * 80)
    print()


if __name__ == "__main__":
    asyncio.run(example_usage())
