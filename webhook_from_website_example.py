#!/usr/bin/env python3
"""
مثال على استقبال البيانات مع حقل from_website في الـ webhook
Example webhook receiver that demonstrates the from_website field
"""

from fastapi import FastAPI, Request
from datetime import datetime
import uvicorn

app = FastAPI(title="Webhook Receiver - from_website Example")

# تخزين النتائج المستلمة
received_results = []


@app.post("/webhook")
async def receive_webhook(request: Request):
    """استقبال البيانات من الـ webhook"""
    
    data = await request.json()
    
    print("\n" + "=" * 80)
    print(f"📥 استلام بيانات جديدة / Received new data")
    print(f"⏰ الوقت / Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    # معلومات الـ job
    job_id = data.get('job_id', 'N/A')
    status = data.get('status', 'N/A')
    
    print(f"\n📋 Job ID: {job_id}")
    print(f"📊 Status: {status}")
    
    # إذا كانت البيانات تحتوي على نتيجة واحدة (real-time)
    if 'result' in data:
        result = data['result']
        current = data.get('current_result', '?')
        total = data.get('total_expected', '?')
        
        print(f"📍 Progress: {current}/{total}")
        print(f"\n🏢 Business: {result.get('business_name', 'N/A')}")
        
        # عرض معلومات الإيميل ومصدره
        email = result.get('email')
        from_website = result.get('from_website')
        
        if email:
            source_icon = "🌐" if from_website else "🗺️"
            source_text = "Website" if from_website else "Google Maps"
            
            print(f"📧 Email: {email}")
            print(f"📍 Source: {source_icon} {source_text}")
            print(f"   from_website: {from_website}")
            
            # تحليل جودة البيانات
            if from_website:
                print(f"   ✅ High quality - من الموقع الرسمي")
            else:
                print(f"   ℹ️  Standard quality - من Google Maps")
        else:
            print(f"📧 Email: Not available")
            print(f"   from_website: {from_website}")
        
        # معلومات إضافية
        if result.get('website'):
            print(f"🌐 Website: {result.get('website')}")
        if result.get('phone'):
            print(f"📞 Phone: {result.get('phone')}")
        if result.get('rating'):
            print(f"⭐ Rating: {result.get('rating')}")
        
        # حفظ النتيجة
        received_results.append(result)
    
    # إذا كانت رسالة إتمام
    elif status == 'completed':
        total_results = data.get('total_results', 0)
        message = data.get('message', '')
        
        print(f"\n✅ {message}")
        print(f"📊 Total results: {total_results}")
        
        # إحصائيات عن الإيميلات
        if received_results:
            with_email = [r for r in received_results if r.get('email')]
            from_website_count = sum(1 for r in with_email if r.get('from_website') == True)
            from_maps_count = sum(1 for r in with_email if r.get('from_website') == False)
            
            print(f"\n📈 Email Statistics:")
            print(f"   Total with email: {len(with_email)}/{len(received_results)}")
            print(f"   From websites: {from_website_count} ({from_website_count/len(with_email)*100:.1f}%)" if with_email else "   From websites: 0")
            print(f"   From Google Maps: {from_maps_count} ({from_maps_count/len(with_email)*100:.1f}%)" if with_email else "   From Google Maps: 0")
    
    print("=" * 80)
    print()
    
    return {"status": "received", "timestamp": datetime.now().isoformat()}


@app.get("/")
async def root():
    """معلومات عن الـ webhook receiver"""
    return {
        "name": "Webhook Receiver - from_website Example",
        "description": "مثال على استقبال البيانات مع حقل from_website",
        "endpoint": "/webhook",
        "received_count": len(received_results),
        "statistics": {
            "total": len(received_results),
            "with_email": len([r for r in received_results if r.get('email')]),
            "from_website": len([r for r in received_results if r.get('email') and r.get('from_website') == True]),
            "from_maps": len([r for r in received_results if r.get('email') and r.get('from_website') == False])
        }
    }


@app.get("/results")
async def get_results():
    """عرض جميع النتائج المستلمة"""
    return {
        "total": len(received_results),
        "results": received_results
    }


@app.delete("/clear")
async def clear_results():
    """مسح جميع النتائج"""
    global received_results
    count = len(received_results)
    received_results = []
    return {"message": f"Cleared {count} results"}


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("🚀 Starting Webhook Receiver - from_website Example")
    print("=" * 80)
    print("\n📍 Webhook URL: http://localhost:8001/webhook")
    print("📊 Stats URL: http://localhost:8001/")
    print("📄 Results URL: http://localhost:8001/results")
    print("\n💡 Usage:")
    print("   1. Start this webhook receiver")
    print("   2. Send a scraping request with webhook_url=http://localhost:8001/webhook")
    print("   3. Watch the console for real-time updates with from_website field")
    print("\n" + "=" * 80)
    print()
    
    uvicorn.run(app, host="0.0.0.0", port=8001)
