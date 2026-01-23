#!/usr/bin/env python3
"""
Test script to verify from_website field functionality
"""

import asyncio
import json
from scraper import scrape_google_maps


async def test_from_website_field():
    """Test that from_website field is properly set."""
    
    print("🧪 Testing from_website field functionality...\n")
    
    # Test with a small number of results
    results = await scrape_google_maps(
        search_term="restaurants in Cairo",
        headless=True,
        max_results=3
    )
    
    print(f"\n📊 Test Results ({len(results)} businesses):\n")
    print("=" * 80)
    
    for idx, result in enumerate(results, 1):
        print(f"\n{idx}. {result.get('business_name', 'N/A')}")
        print(f"   Email: {result.get('email', 'N/A')}")
        print(f"   From Website: {result.get('from_website', 'N/A')}")
        print(f"   Website: {result.get('website', 'N/A')}")
        
        # Verify the logic
        if result.get('email'):
            if result.get('from_website') == True:
                print(f"   ✅ Email extracted from website")
            elif result.get('from_website') == False:
                print(f"   ✅ Email extracted from Google Maps")
            else:
                print(f"   ⚠️  WARNING: from_website field not set correctly!")
        else:
            print(f"   ℹ️  No email found")
            if result.get('from_website') == False:
                print(f"   ✅ from_website correctly set to False (no email)")
            else:
                print(f"   ⚠️  WARNING: from_website should be False when no email!")
    
    print("\n" + "=" * 80)
    
    # Summary
    total = len(results)
    with_email = sum(1 for r in results if r.get('email'))
    from_website = sum(1 for r in results if r.get('email') and r.get('from_website') == True)
    from_maps = sum(1 for r in results if r.get('email') and r.get('from_website') == False)
    
    print(f"\n📈 Summary:")
    print(f"   Total businesses: {total}")
    print(f"   With email: {with_email} ({with_email/total*100:.1f}%)")
    print(f"   Email from website: {from_website} ({from_website/with_email*100:.1f}% of emails)" if with_email > 0 else "   Email from website: 0")
    print(f"   Email from Google Maps: {from_maps} ({from_maps/with_email*100:.1f}% of emails)" if with_email > 0 else "   Email from Google Maps: 0")
    
    # Save sample JSON
    print(f"\n💾 Saving sample JSON output...")
    with open('test_from_website_output.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"   ✅ Saved to: test_from_website_output.json")
    
    print("\n✅ Test completed!\n")


if __name__ == "__main__":
    asyncio.run(test_from_website_field())
