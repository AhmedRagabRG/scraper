#!/usr/bin/env python3
"""
Google Authentication Helper
Save and load Google cookies for authenticated scraping
"""

import json
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright


async def save_google_cookies():
    """
    Interactive script to save Google cookies.
    Run this once with a browser window to login to Google.
    """
    print("🔐 Starting Google login session...")
    print("📝 You will need to:")
    print("   1. Login to your Google account")
    print("   2. Navigate to Google Maps")
    print("   3. Press Enter when done")
    print()
    
    async with async_playwright() as p:
        # Launch browser in NON-headless mode
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            locale='en-US',
        )
        page = await context.new_page()
        
        # Go to Google
        print("🌐 Opening Google...")
        await page.goto('https://accounts.google.com/')
        
        # Wait for user to login
        input("\n✋ Press Enter after you've logged in and visited Google Maps...")
        
        # Go to Google Maps to ensure cookies are set
        print("🗺️  Opening Google Maps...")
        await page.goto('https://www.google.com/maps')
        await asyncio.sleep(3)
        
        # Save cookies
        cookies = await context.cookies()
        cookies_file = Path('google_cookies.json')
        
        with open(cookies_file, 'w') as f:
            json.dump(cookies, f, indent=2)
        
        print(f"\n✅ Cookies saved to {cookies_file}")
        print(f"   Total cookies: {len(cookies)}")
        
        await browser.close()
        
        print("\n🎉 Done! You can now use these cookies for scraping.")


async def load_google_cookies(context):
    """
    Load saved Google cookies into a browser context.
    
    Args:
        context: Playwright browser context
        
    Returns:
        bool: True if cookies loaded successfully
    """
    cookies_file = Path('google_cookies.json')
    
    if not cookies_file.exists():
        print("⚠️ No cookies file found. Run 'python google_auth.py' first.")
        return False
    
    try:
        with open(cookies_file, 'r') as f:
            cookies = json.load(f)
        
        await context.add_cookies(cookies)
        print(f"✅ Loaded {len(cookies)} cookies")
        return True
        
    except Exception as e:
        print(f"❌ Error loading cookies: {e}")
        return False


if __name__ == '__main__':
    print("=" * 60)
    print("Google Maps Authentication Helper")
    print("=" * 60)
    asyncio.run(save_google_cookies())
