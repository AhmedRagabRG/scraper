#!/usr/bin/env python3
"""
Google Maps Reviews Scraper
Extracts reviews from a specific Google Maps place
"""

import asyncio
import random
import re
import os
from datetime import datetime
from typing import List, Dict, Optional
from playwright.async_api import async_playwright, Page, Browser, BrowserContext
from config import proxy_config, ScraperConfig

# Import stealth plugin (supports both v1.x and v2.x)
STEALTH_AVAILABLE = False
_stealth_instance = None
try:
    # v2.x API
    from playwright_stealth import Stealth
    _stealth_instance = Stealth()
    STEALTH_AVAILABLE = True
except ImportError:
    try:
        # v1.x API fallback
        from playwright_stealth import stealth_async
        STEALTH_AVAILABLE = True
    except ImportError:
        print("⚠️ playwright-stealth not installed. Continuing without stealth.")


class GoogleMapsReviewsScraper:
    """Scraper for Google Maps reviews."""

    def __init__(self, headless: bool = True):
        self.headless = headless
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.playwright = None
        self._used_proxies = set()  # Track failed proxies to avoid reuse
        self._debug_dir = 'output/debug'
        os.makedirs(self._debug_dir, exist_ok=True)

    async def _save_debug_page(self, step_name: str) -> str:
        """Save page source HTML and screenshot for debugging.
        Returns the path to the saved HTML file."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        base_name = f"{timestamp}_{step_name}"
        html_path = os.path.join(self._debug_dir, f"{base_name}.html")
        screenshot_path = os.path.join(self._debug_dir, f"{base_name}.png")
        
        try:
            # Save page source
            page_content = await self.page.content()
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(page_content)
            print(f"\U0001f4c4 Debug HTML saved: {html_path} ({len(page_content)} bytes)")
            
            # Also print key info about the page
            page_url = self.page.url
            page_title = await self.page.title()
            print(f"   URL: {page_url}")
            print(f"   Title: {page_title}")
            
            # Print first 500 chars of visible text for quick debugging
            visible_text = await self.page.evaluate("""
                () => {
                    return document.body ? document.body.innerText.substring(0, 500) : 'NO BODY';
                }
            """)
            print(f"   Page text preview: {visible_text[:300]}...")
        except Exception as e:
            print(f"   \u26a0\ufe0f Could not save page source: {e}")
        
        try:
            # Save screenshot
            await self.page.screenshot(path=screenshot_path, full_page=True)
            print(f"\U0001f4f8 Debug screenshot saved: {screenshot_path}")
        except Exception as e:
            print(f"   \u26a0\ufe0f Could not save screenshot: {e}")
        
        return html_path

    async def _setup_browser(self, exclude_proxy: Optional[str] = None):
        """Initialize browser with stealth configurations."""
        if not self.playwright:
            self.playwright = await async_playwright().start()
        
        # Setup proxy if available
        launch_options = {
            'headless': self.headless,
            'args': [
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-blink-features=AutomationControlled',
            ]
        }
        
        self._current_proxy = None
        if ScraperConfig.USE_PROXIES:
            # Try to get a proxy that hasn't failed yet
            available_proxies = [p for p in proxy_config.proxies if p not in self._used_proxies]
            if available_proxies:
                proxy_url = random.choice(available_proxies)
                proxy_dict = proxy_config._parse_proxy_url(proxy_url)
                if proxy_dict:
                    launch_options['proxy'] = proxy_dict
                    self._current_proxy = proxy_url
                    print(f"🌐 Using proxy: {proxy_dict['server']}")
                else:
                    print("⚠️ Failed to parse proxy URL, continuing without proxy")
            else:
                print("⚠️ All proxies exhausted or none available, continuing without proxy")
        else:
            print("ℹ️ Proxies disabled (set USE_PROXIES=true to enable)")
        
        self.browser = await self.playwright.chromium.launch(**launch_options)

        self.context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent=ScraperConfig.get_random_user_agent(),
            locale='en-US',
        )
        
        # Load Google cookies if available
        from pathlib import Path
        import json
        cookies_file = Path('google_cookies.json')
        if cookies_file.exists():
            try:
                # Check if file is empty
                if cookies_file.stat().st_size == 0:
                    print("⚠️ google_cookies.json is empty. Run: python google_auth.py")
                else:
                    with open(cookies_file, 'r') as f:
                        cookies = json.load(f)
                    
                    if cookies and len(cookies) > 0:
                        await self.context.add_cookies(cookies)
                        print(f"✅ Loaded {len(cookies)} Google cookies (authenticated session)")
                    else:
                        print("⚠️ google_cookies.json is empty or invalid")
            except json.JSONDecodeError as e:
                print(f"⚠️ Invalid JSON in google_cookies.json: {e}")
                print("   Please re-run: python google_auth.py")
            except Exception as e:
                print(f"⚠️ Could not load cookies: {e}")
        else:
            print("⚠️ No Google cookies found. Reviews may not load without authentication.")
            print("   Run: python google_auth.py")

        self.page = await self.context.new_page()
        
        # Apply playwright-stealth if available
        if STEALTH_AVAILABLE:
            try:
                if _stealth_instance:
                    # v2.x: apply to page
                    await _stealth_instance.apply_stealth_async(self.page)
                else:
                    # v1.x fallback
                    await stealth_async(self.page)
                print("✓ Stealth mode enabled")
            except Exception as e:
                print(f"⚠️ Stealth apply failed: {e}. Continuing without stealth.")

        # Additional stealth JavaScript
        await self.page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => false,
            });
            
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en'],
            });
        """)

    async def _check_for_captcha(self) -> bool:
        """Check if the page shows a CAPTCHA or is blocked by Google."""
        try:
            page_content = await self.page.content()
            page_url = self.page.url
            page_lower = page_content.lower()
            
            # Check if page is basically empty or very small (sign of block)
            if len(page_content) < 500:
                print(f"🚫 Page content suspiciously small ({len(page_content)} bytes) - possible block")
                return True
            
            captcha_indicators = [
                'recaptcha', 'g-recaptcha', 'captcha',
                'unusual traffic', 'automated queries',
                'sorry/index', 'ipv4.google.com/sorry',
                'detected unusual traffic',
                'are not a robot', 'verify you are human',
                'blocked', 'access denied',
                'consent.google', 'before you continue',
            ]
            
            for indicator in captcha_indicators:
                if indicator in page_lower or indicator in page_url.lower():
                    print(f"🚫 Detected block indicator: '{indicator}'")
                    return True
            
            # Check if Google Maps actually loaded (has map-related elements)
            has_maps_content = await self.page.evaluate("""
                () => {
                    const hasH1 = !!document.querySelector('h1');
                    const hasMap = !!document.querySelector('[id*="map"], [class*="map"], canvas');
                    const hasTabs = document.querySelectorAll('button[role="tab"]').length > 0;
                    return { hasH1, hasMap, hasTabs, 
                             bodyLen: (document.body?.innerText || '').length,
                             url: window.location.href };
                }
            """)
            print(f"📊 Page content check: {has_maps_content}")
            
            return False
        except Exception as e:
            print(f"⚠️ Error checking for CAPTCHA: {e}")
            return False

    async def _handle_consent_dialog(self):
        """Handle Google's cookie consent dialog."""
        try:
            consent_selectors = [
                'button:has-text("Accept all")',
                'button:has-text("I agree")',
                'button:has-text("Reject all")',
            ]

            for selector in consent_selectors:
                try:
                    button = await self.page.wait_for_selector(selector, timeout=3000)
                    if button:
                        await button.click()
                        await asyncio.sleep(1)
                        return
                except:
                    continue
        except:
            pass
    
    async def _force_open_reviews_with_js(self):
        """Force open reviews tab using JavaScript - most reliable method."""
        try:
            print("⏳ Executing JavaScript to open reviews...")
            
            # Wait for page to be ready
            await asyncio.sleep(3)
            
            # Method 1: Find the main Reviews tab (not user profiles)
            # Supports multiple languages for "Reviews" tab detection
            result = await self.page.evaluate("""
                () => {
                    // Multi-language keywords for "Reviews" tab
                    const reviewKeywords = [
                        'review', 'reviews',
                        '\u0645\u0631\u0627\u062C\u0639', '\u062A\u0642\u064A\u064A\u0645',
                        'rezension', 'bewertung',
                        'avis',
                        'rese\u00F1', 'opiniones',
                        'recens', 'valutazion',
                        'avalia\u00E7\u00E3o', 'avalia\u00E7\u00F5es',
                        'yorum',
                        '\u043E\u0442\u0437\u044B\u0432',
                        'recenze',
                        'beoordelingen',
                        '\u30EC\u30D3\u30E5\u30FC', '\u30AF\u30C1\u30B3\u30DF',
                        '\uB9AC\uBDF0',
                        '\u8BC4\u8BBA',
                        '\u0111\u00E1nh gi\u00E1',
                        'ulasan',
                        'recenzj',
                        '\u03BA\u03C1\u03B9\u03C4\u03B9\u03BA',
                    ];
                    
                    // Keywords that indicate NON-review tabs (to avoid wrong clicks)
                    const excludeKeywords = [
                        'overview', 'about', 'menu', 'speisekarte', 'karte',
                        'photos', 'fotos', 'bilder', 'updates', 'contact',
                        'write', '\u0643\u062A\u0627\u0628\u0629', 'schreiben', '\u0625\u0636\u0627\u0641\u0629'
                    ];
                    
                    function isReviewTab(text, ariaLabel) {
                        const combined = (text + ' ' + ariaLabel).toLowerCase();
                        
                        // Check if it matches any exclude keyword
                        for (let ex of excludeKeywords) {
                            if (combined.includes(ex)) return false;
                        }
                        
                        // Check if it matches any review keyword
                        for (let kw of reviewKeywords) {
                            if (combined.includes(kw)) return true;
                        }
                        
                        return false;
                    }
                    
                    // Find all buttons
                    const buttons = Array.from(document.querySelectorAll('button'));
                    
                    // Method 1: Look for tabs specifically (role="tab")
                    const tabs = buttons.filter(btn => btn.getAttribute('role') === 'tab');
                    if (tabs.length > 0) {
                        // First pass: look for tab matching review keywords
                        for (let tab of tabs) {
                            const text = (tab.innerText || tab.textContent || '').toLowerCase();
                            const ariaLabel = (tab.getAttribute('aria-label') || '').toLowerCase();
                            
                            if (isReviewTab(text, ariaLabel)) {
                                console.log('Found Reviews tab:', tab.innerText);
                                tab.click();
                                return { success: true, method: 'reviews_tab', text: tab.innerText };
                            }
                        }
                        
                        // Second pass: look for tab with a number (review count) that is NOT overview/menu/about
                        for (let tab of tabs) {
                            const text = (tab.innerText || tab.textContent || '').trim();
                            const ariaLabel = (tab.getAttribute('aria-label') || '').toLowerCase();
                            const combined = (text + ' ' + ariaLabel).toLowerCase();
                            
                            // Skip tabs that match known non-review labels
                            let isExcluded = false;
                            for (let ex of excludeKeywords) {
                                if (combined.includes(ex)) { isExcluded = true; break; }
                            }
                            if (isExcluded) continue;
                            
                            // Check if tab text contains a number (e.g., "Rezensionen\n42")
                            const hasNumber = /\\d+/.test(text);
                            if (hasNumber) {
                                console.log('Found tab with number (likely reviews):', text);
                                tab.click();
                                return { success: true, method: 'tab_with_count', text: text };
                            }
                        }
                        
                        // DO NOT blindly click second tab - log what's available instead
                        const tabsInfo = tabs.map(t => (t.innerText || '').substring(0, 30)).join(' | ');
                        console.log('Available tabs: ' + tabsInfo);
                    }
                    
                    // Method 2: Find button with ONLY "Reviews" text (no names)
                    for (let btn of buttons) {
                        const text = btn.innerText || btn.textContent || '';
                        const ariaLabel = btn.getAttribute('aria-label') || '';
                        
                        // Check if it's JUST the reviews text (no newlines = no user names)
                        if (!text.includes('\\n') && text.trim().length < 30) {
                            if (isReviewTab(text, ariaLabel)) {
                                console.log('Found simple reviews button:', text);
                                btn.click();
                                return { success: true, method: 'simple_review_button', text: text };
                            }
                        }
                    }
                    
                    // Method 3: Try clicking on reviews count text (e.g., "42 reviews" or "42 Rezensionen")
                    const allElements = document.querySelectorAll('button, a, [role="tab"], [role="button"]');
                    for (let el of allElements) {
                        const text = (el.innerText || el.textContent || '').toLowerCase();
                        // Match patterns like "42 reviews", "42 Rezensionen", "42 avis", etc.
                        const match = text.match(/(\\d+)\\s+/);
                        if (match) {
                            for (let kw of reviewKeywords) {
                                if (text.includes(kw)) {
                                    console.log('Found review count element:', el.innerText);
                                    el.click();
                                    return { success: true, method: 'review_count_element', text: el.innerText };
                                }
                            }
                        }
                    }
                    
                    return { success: false, buttons_count: buttons.length, tabs_count: tabs ? tabs.length : 0 };
                }
            """)
            
            print(f"📊 JavaScript result: {result}")
            
            if result.get('success'):
                print(f"✓ Opened reviews using: {result.get('method')}")
                await asyncio.sleep(5)  # Wait for reviews to load
                return True
            else:
                print(f"⚠️ JavaScript couldn't find reviews tab")
                print(f"   Found {result.get('buttons_count', 0)} buttons, {result.get('tabs_count', 0)} tabs")
                
                # Debug: Print tabs info
                tabs_info = await self.page.evaluate("""
                    () => {
                        const tabs = Array.from(document.querySelectorAll('button[role="tab"]'));
                        return tabs.map((tab, i) => ({
                            index: i,
                            text: (tab.innerText || '').substring(0, 50),
                            aria: tab.getAttribute('aria-label') || ''
                        }));
                    }
                """)
                print("🔍 Available tabs:")
                for info in tabs_info:
                    print(f"  Tab[{info['index']}] text='{info['text']}' aria='{info['aria'][:50]}'")
                
                return False
                
        except Exception as e:
            print(f"❌ Error in JavaScript execution: {e}")
            return False

    async def _click_reviews_tab(self):
        """Click on the reviews tab."""
        try:
            # Wait for page to load
            await asyncio.sleep(3)
            
            # Debug: Save page content
            try:
                content = await self.page.content()
                print(f"📄 Page loaded, content length: {len(content)}")
            except:
                pass
            
            # First, check if we're already on the reviews view
            already_on_reviews = await self.page.evaluate("""
                () => {
                    // Check if there are review elements visible
                    const hasReviewElements = document.querySelector('div[data-review-id]') ||
                                             document.querySelector('div.jftiEf') ||
                                             document.querySelector('span[role="img"][aria-label*="star"]');
                    
                    // Check if reviews tab is already selected
                    const reviewsTab = document.querySelector('button[aria-label*="Reviews"][aria-selected="true"]') ||
                                      document.querySelector('button[data-tab-index="1"][aria-selected="true"]');
                    
                    return hasReviewElements || reviewsTab;
                }
            """)
            
            if already_on_reviews:
                print("✓ Already on reviews view, skipping tab click")
                return True
            
            # Try to find and click reviews tab - with more selectors (multi-language)
            reviews_selectors = [
                'button[aria-label*="Reviews"]',
                'button[aria-label*="reviews"]',
                'button[aria-label*="Rezension"]',
                'button[aria-label*="Bewertung"]',
                'button[aria-label*="avis"]',
                'button[aria-label*="reseña"]',
                'button:has-text("Reviews")',
                'button:has-text("reviews")',
                'button:has-text("Rezensionen")',
                'button:has-text("Bewertungen")',
                'button:has-text("Avis")',
                'button:has-text("Reseñas")',
                'div[role="tab"]:has-text("Reviews")',
                '[role="tab"]:has-text("Reviews")',
                'button[jsaction*="pane.reviewChart"]',
            ]
            
            clicked = False
            for selector in reviews_selectors:
                try:
                    # Wait a bit longer for the button to appear
                    button = await self.page.wait_for_selector(selector, timeout=5000)
                    if button:
                        # Check if it's visible
                        is_visible = await button.is_visible()
                        if not is_visible:
                            continue
                        
                        # Scroll to button
                        await button.scroll_into_view_if_needed()
                        await asyncio.sleep(0.5)
                        
                        # Try multiple click methods
                        try:
                            # Method 1: Regular click
                            await button.click()
                        except:
                            try:
                                # Method 2: JavaScript click
                                await self.page.evaluate('(btn) => btn.click()', button)
                            except:
                                # Method 3: Force click
                                await button.click(force=True)
                        
                        print(f"✓ Clicked Reviews tab using: {selector}")
                        await asyncio.sleep(4)
                        clicked = True
                        break
                except Exception as e:
                    continue
            
            if not clicked:
                print("⚠️ Could not find Reviews tab")
                # Debug: List all buttons
                try:
                    buttons = await self.page.query_selector_all('button')
                    print(f"🔍 Found {len(buttons)} buttons on page")
                    
                    # Try to find buttons with text containing "review" (case insensitive)
                    for btn in buttons[:20]:  # Check first 20 buttons
                        try:
                            text = await btn.inner_text()
                            aria = await btn.get_attribute('aria-label')
                            if text and 'review' in text.lower():
                                print(f"  Found button with text: {text}")
                            if aria and 'review' in aria.lower():
                                print(f"  Found button with aria-label: {aria}")
                        except:
                            pass
                except:
                    pass
                return False
            
            return True
            
        except Exception as e:
            print(f"⚠️ Error clicking reviews tab: {e}")
            return False

    async def _sort_by_lowest_rating(self):
        """Sort reviews by lowest rating first."""
        try:
            print("🔽 Sorting reviews by lowest rating...")
            await asyncio.sleep(2)
            
            # Try to find and click the sort button/dropdown
            sort_selectors = [
                'button[aria-label*="Sort"]',
                'button[aria-label*="sort"]',
                'button[data-value*="Sort"]',
                'button:has-text("Sort")',
                'button:has-text("Most relevant")',
                'button.e2moi',  # Common sort button class
            ]
            
            sort_clicked = False
            for selector in sort_selectors:
                try:
                    sort_button = await self.page.wait_for_selector(selector, timeout=3000)
                    if sort_button:
                        await sort_button.scroll_into_view_if_needed()
                        await asyncio.sleep(0.5)
                        await self.page.evaluate('(btn) => btn.click()', sort_button)
                        print(f"✓ Clicked sort button using: {selector}")
                        await asyncio.sleep(2)
                        sort_clicked = True
                        break
                except:
                    continue
            
            if not sort_clicked:
                print("⚠️ Could not find sort button, continuing with default sort")
                return False
            
            # Now try to click "Lowest rating" option
            lowest_rating_selectors = [
                'div[role="menuitemradio"][data-index="3"]',  # Usually the 4th option (0-indexed)
                'div[role="menuitemradio"]:has-text("Lowest")',
                'div[role="menuitemradio"][aria-label*="Lowest"]',
                'li:has-text("Lowest rating")',
                'div:has-text("Lowest rating")',
                '[data-value="4"]',  # Alternative data attribute
            ]
            
            lowest_clicked = False
            for selector in lowest_rating_selectors:
                try:
                    option = await self.page.wait_for_selector(selector, timeout=2000)
                    if option:
                        await self.page.evaluate('(opt) => opt.click()', option)
                        print(f"✓ Selected 'Lowest rating' using: {selector}")
                        await asyncio.sleep(3)
                        lowest_clicked = True
                        break
                except:
                    continue
            
            if not lowest_clicked:
                print("⚠️ Could not select 'Lowest rating' option")
                # Close the dropdown by pressing Escape
                try:
                    await self.page.keyboard.press('Escape')
                    await asyncio.sleep(1)
                    print("✓ Closed sort dropdown, continuing with default sort")
                except:
                    pass
                return False
            
            print("✓ Successfully sorted by lowest rating")
            return True
            
        except Exception as e:
            print(f"⚠️ Error sorting reviews: {e}")
            # Try to close any open dropdown
            try:
                await self.page.keyboard.press('Escape')
                await asyncio.sleep(1)
            except:
                pass
            return False

    async def _scroll_reviews(self, max_reviews: Optional[int] = None):
        """Scroll through reviews to load more."""
        print("📜 Scrolling through reviews...")
        
        try:
            # Wait for reviews container to load
            await asyncio.sleep(4)
            
            # Debug: Check page structure
            try:
                all_divs = await self.page.evaluate("""
                    () => {
                        return {
                            total_divs: document.querySelectorAll('div').length,
                            feed_divs: document.querySelectorAll('div[role="feed"]').length,
                            review_containers: document.querySelectorAll('[class*="review"]').length
                        }
                    }
                """)
                print(f"🔍 Page structure: {all_divs}")
            except:
                pass
            
            # Try multiple selectors for reviews - expanded and prioritized list
            review_selectors = [
                'div.jftiEf[data-review-id]',  # Most specific
                'div[data-review-id][aria-label]',  # Has aria-label
                'div.jftiEf',  # Common review container
                'div[jsaction*="review.in"]',  # Has review-related actions
            ]
            
            reviews_found = False
            working_selector = None
            
            # First, try the known selectors
            for selector in review_selectors:
                test_count = await self.page.evaluate(f"""
                    () => {{
                        const elements = document.querySelectorAll('{selector}');
                        // For fontBodyMedium, check if they look like reviews
                        if ('{selector}' === 'div.fontBodyMedium') {{
                            let reviewCount = 0;
                            elements.forEach(el => {{
                                const text = el.innerText || '';
                                // Check if it has review-like content (name, date, rating, text)
                                if (text.length > 50 && (
                                    text.includes('ago') || 
                                    text.includes('week') || 
                                    text.includes('month') ||
                                    text.includes('day') ||
                                    text.includes('year')
                                )) {{
                                    reviewCount++;
                                }}
                            }});
                            return reviewCount;
                        }}
                        return elements.length;
                    }}
                """)
                print(f"  Testing {selector}: {test_count} elements")
                if test_count > 0:
                    print(f"✓ Found reviews using selector: {selector}")
                    reviews_found = True
                    working_selector = selector
                    break
            
            # If no reviews found with known selectors, try a more generic approach
            if not reviews_found:
                print("  Trying generic review detection...")
                generic_count = await self.page.evaluate("""
                    () => {
                        // Look for elements that contain star ratings
                        const allDivs = document.querySelectorAll('div');
                        let reviewElements = [];
                        
                        // Multi-language date keywords
                        const dateKeywords = [
                            'ago', 'week', 'month', 'day', 'year',
                            'vor', 'woche', 'monat', 'tag', 'jahr',
                            'il y a', 'semaine', 'mois', 'jour', 'an',
                            'hace', 'semana', 'mes', 'd\\u00EDa', 'a\\u00F1o',
                            '\\u0645\\u0646\\u0630', '\\u0623\\u0633\\u0628\\u0648\\u0639', '\\u0634\\u0647\\u0631', '\\u064A\\u0648\\u0645', '\\u0633\\u0646\\u0629',
                            'fa', 'settimana', 'mese', 'giorno', 'anno',
                            '\\u00F6nce', 'hafta', 'ay', 'g\\u00FCn', 'y\\u0131l',
                        ];
                        
                        allDivs.forEach(div => {
                            // Check if this div has a star rating indicator
                            const hasStars = div.querySelector('span[role="img"][aria-label*="star"]') ||
                                           div.querySelector('span[aria-label*="stars"]') ||
                                           div.querySelector('span[aria-label*="Stern"]') ||
                                           div.querySelector('[aria-label*="Star rating"]');
                            
                            // Check if it has date-like text (multi-language)
                            const text = (div.innerText || '').toLowerCase();
                            const hasDate = dateKeywords.some(kw => text.includes(kw));
                            
                            // Check if it has substantial text (likely review content)
                            const hasContent = text.length > 50;
                            
                            if (hasStars && hasDate && hasContent) {
                                // Make sure it's not already counted (avoid nested divs)
                                let isNested = false;
                                reviewElements.forEach(existing => {
                                    if (existing.contains(div) || div.contains(existing)) {
                                        isNested = true;
                                    }
                                });
                                
                                if (!isNested) {
                                    reviewElements.push(div);
                                    // Mark it for easy selection later
                                    div.setAttribute('data-detected-review', 'true');
                                }
                            }
                        });
                        
                        return reviewElements.length;
                    }
                """)
                
                if generic_count > 0:
                    print(f"✓ Found {generic_count} reviews using generic detection")
                    working_selector = 'div[data-detected-review="true"]'
                    reviews_found = True
                else:
                    print(f"  Generic detection found: {generic_count} elements")
            
            if not reviews_found:
                print("⚠️ No reviews found with any selector.")
                # Save page for debugging
                try:
                    content = await self.page.content()
                    with open('debug_reviews_page.html', 'w', encoding='utf-8') as f:
                        f.write(content)
                    print("💾 Saved page to debug_reviews_page.html for inspection")
                except:
                    pass
                
                # Try aggressive scrolling anyway
                print("🔄 Trying aggressive scrolling...")
                for i in range(5):
                    await self.page.evaluate("""
                        () => {
                            window.scrollTo(0, document.body.scrollHeight);
                            const divs = document.querySelectorAll('div[role="feed"]');
                            divs.forEach(div => div.scrollTop = div.scrollHeight);
                        }
                    """)
                    await asyncio.sleep(2)
                
                return 0
            
            previous_count = 0
            no_change_count = 0
            max_no_change = 15  # Stop if no new reviews after 15 attempts
            scroll_attempts = 0
            max_scroll_attempts = 300  # Increased from 100 to 300 for places with many reviews
            
            print("  Starting scroll loop...")
            
            while no_change_count < max_no_change and scroll_attempts < max_scroll_attempts:
                scroll_attempts += 1
                
                # Count current reviews using multiple selectors
                current_count = await self.page.evaluate("""
                    () => {
                        // Try multiple selectors
                        let reviews = document.querySelectorAll('div[data-review-id]');
                        if (reviews.length === 0) {
                            reviews = document.querySelectorAll('div.jftiEf');
                        }
                        if (reviews.length === 0) {
                            reviews = document.querySelectorAll('div[jsaction*="review"]');
                        }
                        if (reviews.length === 0) {
                            reviews = document.querySelectorAll('div[data-detected-review="true"]');
                        }
                        console.log('Current reviews count:', reviews.length);
                        return reviews.length;
                    }
                """)
                
                print(f"  Scroll #{scroll_attempts}: {current_count} reviews (no_change: {no_change_count}/{max_no_change})")
                
                # Check if we have enough reviews
                if max_reviews and current_count >= max_reviews:
                    print(f"✓ Reached target of {max_reviews} reviews")
                    break
                
                # AGGRESSIVE SCROLLING - Find correct container and scroll
                try:
                    scroll_result = await self.page.evaluate("""
                        () => {
                            // CRITICAL: Find the correct feed - the one that contains actual reviews
                            // NOT the search results feed on the left
                            
                            let reviewsFeed = null;
                            let method = 'none';
                            
                            // Strategy 1: Find feed that contains review elements
                            const feeds = Array.from(document.querySelectorAll('div[role="feed"]'));
                            
                            for (let feed of feeds) {
                                // Check if this feed contains reviews (not search results)
                                const hasReviews = feed.querySelector('div[data-review-id]') || 
                                                  feed.querySelector('div.jftiEf');
                                
                                // Also check it's NOT the search results feed (has place links)
                                const hasPlaceLinks = feed.querySelectorAll('a[href*="/place/"]').length > 3;
                                
                                if (hasReviews && !hasPlaceLinks) {
                                    reviewsFeed = feed;
                                    method = 'feed_with_reviews';
                                    break;
                                }
                            }
                            
                            // Strategy 2: Find scrollable div with class m6QErb that contains reviews
                            if (!reviewsFeed) {
                                const scrollableDivs = document.querySelectorAll('.m6QErb.DxyBCb.kA9KIf.dS8AEf');
                                for (let div of scrollableDivs) {
                                    const hasReviews = div.querySelector('div[data-review-id]') || 
                                                      div.querySelector('div.jftiEf');
                                    if (hasReviews) {
                                        reviewsFeed = div;
                                        method = 'scrollable_div';
                                        break;
                                    }
                                }
                            }
                            
                            // Strategy 3: Find scrollable parent of a review element
                            if (!reviewsFeed) {
                                const firstReview = document.querySelector('div[data-review-id]') || document.querySelector('div.jftiEf');
                                if (firstReview) {
                                    let parent = firstReview.parentElement;
                                    while (parent && parent !== document.body) {
                                        const style = window.getComputedStyle(parent);
                                        const isScrollable = (style.overflowY === 'auto' || style.overflowY === 'scroll') 
                                                          && parent.scrollHeight > parent.clientHeight;
                                        if (isScrollable) {
                                            reviewsFeed = parent;
                                            method = 'scrollable_parent';
                                            break;
                                        }
                                        parent = parent.parentElement;
                                    }
                                }
                            }
                            
                            // Strategy 4: Find any div with class m6QErb (common Google Maps scrollable panel)
                            if (!reviewsFeed) {
                                const panels = document.querySelectorAll('.m6QErb');
                                for (let div of panels) {
                                    if (div.scrollHeight > div.clientHeight + 100) {
                                        const hasReviews = div.querySelector('div[data-review-id]') || 
                                                          div.querySelector('div.jftiEf');
                                        if (hasReviews) {
                                            reviewsFeed = div;
                                            method = 'm6QErb_panel';
                                            break;
                                        }
                                    }
                                }
                            }
                            
                            // Strategy 5: Find by checking parent structure (reviews are usually in right panel)
                            if (!reviewsFeed) {
                                const allScrollable = document.querySelectorAll('div[style*="overflow"]');
                                for (let div of allScrollable) {
                                    const hasReviews = div.querySelector('div[data-review-id]') || 
                                                      div.querySelector('div.jftiEf');
                                    if (hasReviews) {
                                        reviewsFeed = div;
                                        method = 'overflow_div';
                                        break;
                                    }
                                }
                            }
                            
                            if (reviewsFeed) {
                                const beforeScroll = reviewsFeed.scrollTop;
                                reviewsFeed.scrollTop += 1000;  // Increased from 800 to 1000
                                const afterScroll = reviewsFeed.scrollTop;
                                
                                console.log(`Scrolling using ${method}: ${beforeScroll} -> ${afterScroll}`);
                                
                                return {
                                    success: true,
                                    method: method,
                                    scrolled: afterScroll - beforeScroll,
                                    position: afterScroll
                                };
                            } else {
                                console.log('⚠️ Could not find reviews container!');
                                return { success: false };
                            }
                        }
                    """)
                    
                    if scroll_result.get('success'):
                        if scroll_result.get('scrolled') == 0:
                            print(f"  ⚠️ Scroll position didn't change - might be at bottom")
                    else:
                        print(f"  ⚠️ Could not find scroll container")
                    
                    # Also scroll last review into view as backup
                    await self.page.evaluate("""
                        () => {
                            let reviews = document.querySelectorAll('div[data-review-id]');
                            if (reviews.length === 0) reviews = document.querySelectorAll('div.jftiEf');
                            
                            if (reviews.length > 0) {
                                const lastReview = reviews[reviews.length - 1];
                                lastReview.scrollIntoView({ behavior: 'smooth', block: 'end' });
                            }
                        }
                    """)
                    
                except Exception as scroll_error:
                    print(f"  ❌ Scroll error: {scroll_error}")
                
                # Wait for content to load
                await asyncio.sleep(2.5)
                
                # CRITICAL: Click any "More reviews" / "Load more" / expand buttons
                try:
                    await self.page.evaluate("""
                        () => {
                            // Click "More" / "See more reviews" buttons (multi-language)
                            const moreKeywords = [
                                'more review', 'more comments', 'load more', 'show more',
                                'weitere rezensionen', 'mehr bewertungen', 'mehr anzeigen',
                                'plus d\\'avis', 'afficher plus', 'voir plus',
                                'm\u00e1s rese\u00f1as', 'mostrar m\u00e1s', 'cargar m\u00e1s',
                                'altre recensioni', 'mostra altro',
                                'daha fazla yorum', 'daha fazla g\u00f6ster',
                                '\u0627\u0644\u0645\u0632\u064a\u062f', '\u0639\u0631\u0636 \u0627\u0644\u0645\u0632\u064a\u062f',
                                '\u043e\u0449\u0435 \u043e\u0442\u0437\u044b\u0432\u044b', '\u043f\u043e\u043a\u0430\u0437\u0430\u0442\u044c \u0435\u0449\u0435',
                            ];
                            
                            // Find and click buttons/links that load more reviews
                            const clickables = document.querySelectorAll('button, a, [role="button"], [jsaction]');
                            for (let el of clickables) {
                                const text = (el.innerText || el.textContent || '').toLowerCase().trim();
                                const ariaLabel = (el.getAttribute('aria-label') || '').toLowerCase();
                                const combined = text + ' ' + ariaLabel;
                                
                                for (let kw of moreKeywords) {
                                    if (combined.includes(kw)) {
                                        console.log('Clicking "more reviews" button:', text.substring(0, 50));
                                        el.click();
                                        return 'clicked_more: ' + text.substring(0, 50);
                                    }
                                }
                            }
                            
                            // Also click any "Next page" type pagination
                            const nextButtons = document.querySelectorAll('button[aria-label*="Next"], button[aria-label*="next"], button[aria-label*="N\u00e4chste"]');
                            for (let btn of nextButtons) {
                                if (!btn.disabled) {
                                    btn.click();
                                    return 'clicked_next_page';
                                }
                            }
                            
                            return 'no_more_button_found';
                        }
                    """)
                except:
                    pass
                
                # Also try to expand "See all reviews" link if present
                try:
                    await self.page.evaluate("""
                        () => {
                            // Sometimes Google shows a "See all X reviews" link
                            const links = document.querySelectorAll('a, button');
                            for (let link of links) {
                                const text = (link.innerText || '').toLowerCase();
                                const ariaLabel = (link.getAttribute('aria-label') || '').toLowerCase();
                                // Match "All reviews", "See all", "Alle Rezensionen", etc
                                const allKeywords = ['all review', 'see all', 'alle rezension', 'alle bewertung', 
                                                     'tous les avis', 'todas las rese', 'tutte le recens',
                                                     't\u00fcm yorum', '\u062c\u0645\u064a\u0639 \u0627\u0644\u062a\u0642\u064a\u064a\u0645'];
                                for (let kw of allKeywords) {
                                    if ((text + ' ' + ariaLabel).includes(kw)) {
                                        link.click();
                                        console.log('Clicked "all reviews" link');
                                        return true;
                                    }
                                }
                            }
                            return false;
                        }
                    """)
                except:
                    pass
                
                # Track progress
                if current_count == previous_count:
                    no_change_count += 1
                    
                    # If stuck for 5 attempts, try extra aggressive scroll
                    if no_change_count == 5:
                        print(f"\n🔄 Stuck at {current_count} reviews, trying aggressive strategies...")
                        
                        # Strategy A: Try keyboard scrolling
                        for _ in range(3):
                            await self.page.keyboard.press('End')
                            await asyncio.sleep(1)
                            await self.page.keyboard.press('PageDown')
                            await asyncio.sleep(1)
                        
                        # Strategy B: Try to scroll the entire page body
                        await self.page.evaluate("""
                            () => {
                                // Scroll all possible containers
                                document.documentElement.scrollTop = document.documentElement.scrollHeight;
                                document.body.scrollTop = document.body.scrollHeight;
                                
                                // Find ALL scrollable divs and scroll them
                                const allDivs = document.querySelectorAll('div');
                                for (let div of allDivs) {
                                    if (div.scrollHeight > div.clientHeight + 200) {
                                        div.scrollTop = div.scrollHeight;
                                    }
                                }
                            }
                        """)
                        await asyncio.sleep(3)
                    
                    # If stuck for 8 attempts, try to click on the reviews sorting dropdown and reselect
                    if no_change_count == 8:
                        print(f"\n🔄 Still stuck at {current_count} reviews, trying sort toggle...")
                        try:
                            # Click sort button to trigger a re-render
                            sort_btn = await self.page.query_selector('button[aria-label*="Sort"], button[data-value*="Sort"], button.e2moi')
                            if sort_btn:
                                await sort_btn.click()
                                await asyncio.sleep(2)
                                # Click "Newest" then back to "Most relevant"
                                newest = await self.page.query_selector('div[role="menuitemradio"][data-index="1"]')
                                if newest:
                                    await newest.click()
                                    await asyncio.sleep(3)
                                    print("   Toggled sort to Newest to trigger reload")
                        except:
                            pass
                else:
                    no_change_count = 0  # Reset counter when we make progress
                
                previous_count = current_count
                
                # Debug every 10 attempts
                if scroll_attempts % 10 == 0:
                    print(f"\n📊 Progress: {current_count} reviews after {scroll_attempts} attempts (no_change: {no_change_count})")
            
            print(f"\n✓ Finished scrolling. Total reviews visible: {current_count}")
            return current_count
            
        except Exception as e:
            print(f"⚠️ Error scrolling reviews: {e}")
            return 0

    async def _extract_reviews(self, max_reviews: Optional[int] = None, on_review_callback=None) -> List[Dict]:
        """Extract review details from the page."""
        reviews = []
        seen_reviewers = set()  # Track seen reviews to avoid duplicates
        
        try:
            # Try multiple selectors to find review elements
            # IMPORTANT: Use specific selectors to avoid wrapper divs
            review_elements = []
            selectors_to_try = [
                'div.jftiEf[data-review-id]',  # Most specific - review content with ID
                'div.jftiEf',  # Review content divs
                'div[data-review-id][aria-label]',  # Has aria-label (actual content)
                'div[jsaction*="review.in"][data-review-id]',  # Has mouse events
            ]
            
            for selector in selectors_to_try:
                review_elements = await self.page.query_selector_all(selector)
                if len(review_elements) > 0:
                    print(f"✓ Using selector: {selector} - Found {len(review_elements)} elements")
                    break
            
            if len(review_elements) == 0:
                print("⚠️ No reviews found with any selector")
                return reviews
            
            total = len(review_elements)
            if max_reviews:
                total = min(total, max_reviews)
            
            print(f"📊 Extracting {total} reviews (with deduplication)...")
            
            for idx, review_elem in enumerate(review_elements[:total], 1):
                try:
                    print(f"  Processing {idx}/{total}...", end='\r')
                    
                    review_data = {
                        'reviewer_name': None,
                        'review_date': None,
                        'rating': None,
                        'review_text': None,
                        'pictures': 'no',
                        'company_reply': 'no',
                        'review_url': None
                    }
                    
                    # Extract reviewer name - try multiple selectors
                    try:
                        name_selectors = [
                            'div[class*="d4r55"]',
                            'button[aria-label]',
                            'a[aria-label]',
                            'div.WNxzHc span',
                        ]
                        for selector in name_selectors:
                            name_elem = await review_elem.query_selector(selector)
                            if name_elem:
                                text = await name_elem.inner_text()
                                if text and len(text.strip()) > 0:
                                    review_data['reviewer_name'] = text.strip()
                                    break
                    except:
                        pass
                    
                    # Extract rating - try multiple methods
                    try:
                        # Method 1: aria-label (multi-language: star, Stern, étoile, estrella)
                        rating_elem = await review_elem.query_selector('span[role="img"][aria-label*="star"], span[role="img"][aria-label*="Stern"], span[role="img"][aria-label*="étoile"], span[role="img"][aria-label*="estrella"]')
                        if rating_elem:
                            aria_label = await rating_elem.get_attribute('aria-label')
                            rating_match = re.search(r'(\d+)', aria_label)
                            if rating_match:
                                review_data['rating'] = int(rating_match.group(1))
                        
                        # Method 2: count filled stars
                        if not review_data['rating']:
                            stars = await review_elem.query_selector_all('span[aria-label*="Rated"]')
                            if stars and len(stars) > 0:
                                aria = await stars[0].get_attribute('aria-label')
                                match = re.search(r'(\d+)', aria)
                                if match:
                                    review_data['rating'] = int(match.group(1))
                    except:
                        pass
                    
                    # Extract review date - try multiple selectors
                    try:
                        date_keywords = [
                            'ago', 'week', 'month', 'day', 'year',       # English
                            'vor', 'woche', 'monat', 'tag', 'jahr',     # German
                            'il y a', 'semaine', 'mois', 'jour', 'an',  # French
                            'hace', 'semana', 'mes', 'día', 'año',      # Spanish
                            'منذ', 'أسبوع', 'شهر', 'يوم', 'سنة',       # Arabic
                            'fa', 'settimana', 'mese', 'giorno', 'anno', # Italian
                            'önce', 'hafta', 'ay', 'gün', 'yıl',        # Turkish
                        ]
                        date_selectors = [
                            'span[class*="rsqaWe"]',
                            'span.DU9Pgb',
                            'span[aria-label]',
                        ]
                        for selector in date_selectors:
                            date_elem = await review_elem.query_selector(selector)
                            if date_elem:
                                text = await date_elem.inner_text()
                                # Check if it looks like a date (multi-language)
                                if any(word in text.lower() for word in date_keywords):
                                    review_data['review_date'] = text.strip()
                                    break
                    except:
                        pass
                    
                    # Extract review text
                    try:
                        # Try to click "More" button if exists
                        more_button_selectors = [
                            'button[aria-label="See more"]',
                            'button[jsaction*="review.expandReview"]',
                            'button.w8nwRe',
                        ]
                        for btn_selector in more_button_selectors:
                            more_buttons = await review_elem.query_selector_all(btn_selector)
                            for btn in more_buttons:
                                try:
                                    await btn.click()
                                    await asyncio.sleep(0.3)
                                except:
                                    pass
                        
                        # Get review text - try multiple selectors
                        text_selectors = [
                            'span[class*="wiI7pd"]',
                            'span[jsan*="review"]',
                            'div.MyEned span',
                            'span.Ahvqpe',
                        ]
                        for selector in text_selectors:
                            text_elem = await review_elem.query_selector(selector)
                            if text_elem:
                                text = await text_elem.inner_text()
                                if text and len(text.strip()) > 0:
                                    review_data['review_text'] = text.strip()
                                    break
                    except:
                        pass
                    
                    # Check for pictures - BALANCED: Detect actual review photos
                    try:
                        has_images = False
                        
                        # Debug first 2 reviews to see what we find
                        if idx <= 2:
                            debug_buttons = await review_elem.evaluate("""
                                (element) => {
                                    const buttons = Array.from(element.querySelectorAll('button'));
                                    return buttons.map(b => ({
                                        aria: b.getAttribute('aria-label') || '',
                                        class: b.className,
                                        hasImg: !!b.querySelector('img')
                                    })).filter(b => 
                                        b.aria.toLowerCase().includes('photo') || 
                                        b.aria.toLowerCase().includes('image') ||
                                        b.class.includes('photo')
                                    );
                                }
                            """)
                            print(f"\n🔍 Review {idx} photo buttons: {debug_buttons}")
                        
                        # Method 1: Look for buttons with photo count in aria-label
                        photo_buttons = await review_elem.query_selector_all('button[aria-label*="photo"], button[aria-label*="Photo"], button[aria-label*="image"], button[aria-label*="Image"]')
                        
                        for btn in photo_buttons:
                            try:
                                aria_label = await btn.get_attribute('aria-label') or ''
                                aria_lower = aria_label.lower()
                                
                                # Skip profile pictures
                                if 'profile' in aria_lower or 'avatar' in aria_lower:
                                    continue
                                
                                # Pattern 1: Number + photo (e.g., "3 photos", "1 photo")
                                import re
                                match = re.search(r'(\d+)\s*(photo|image)', aria_lower)
                                if match:
                                    photo_count = int(match.group(1))
                                    if photo_count > 0:
                                        has_images = True
                                        if idx <= 2:
                                            print(f"  ✅ Found {photo_count} photos via count")
                                        break
                                
                                # Pattern 2: "photo" or "image" without profile keyword
                                # This handles cases like "Open photo" or "View image"
                                if ('photo' in aria_lower or 'image' in aria_lower):
                                    # Additional check: must have an img element inside
                                    has_img = await btn.query_selector('img')
                                    if has_img:
                                        # Check img src to make sure it's not a tiny profile pic
                                        img_src = await has_img.get_attribute('src') or ''
                                        # Review photos usually have larger dimensions in URL
                                        # Profile pics usually have =s40, =s48, etc. (small sizes)
                                        # Review photos have =w250, =w500, etc.
                                        if '=w' in img_src or '=h' in img_src:
                                            # Large image indicator
                                            size_match = re.search(r'=w(\d+)|=h(\d+)', img_src)
                                            if size_match:
                                                size = int(size_match.group(1) or size_match.group(2) or 0)
                                                if size > 100:  # Larger than profile pics
                                                    has_images = True
                                                    if idx <= 2:
                                                        print(f"  ✅ Found photo via img size: {size}px")
                                                    break
                            except:
                                pass
                        
                        # Method 2: Check for button with data-photo-index
                        if not has_images:
                            photo_index_btns = await review_elem.query_selector_all('button[data-photo-index]')
                            if len(photo_index_btns) > 0:
                                has_images = True
                                if idx <= 2:
                                    print(f"  ✅ Found photos via data-photo-index")
                        
                        review_data['pictures'] = 'yes' if has_images else 'no'
                        
                    except Exception as pic_error:
                        review_data['pictures'] = 'no'
                    
                    # Extract company reply - try multiple selectors
                    try:
                        reply_selectors = [
                            'div[class*="CDe7pd"]',
                            'div[aria-label*="Response from"]',
                            'div[aria-label*="Response"]',
                            'div.wiI7pd',
                            'button[aria-label*="response"]',
                        ]
                        has_reply = False
                        for selector in reply_selectors:
                            reply_elem = await review_elem.query_selector(selector)
                            if reply_elem:
                                reply_text = await reply_elem.inner_text()
                                # Check if it's actually a reply (not empty and not same as review)
                                if reply_text and reply_text.strip() and len(reply_text.strip()) > 5:
                                    # Check for "Response from" or owner indicator
                                    reply_lower = reply_text.lower()
                                    if any(keyword in reply_lower for keyword in ['response', 'owner', 'replied', 'reply']):
                                        has_reply = True
                                        break
                        
                        if has_reply:
                            review_data['company_reply'] = 'yes'
                        else:
                            review_data['company_reply'] = 'no'
                    except:
                        review_data['company_reply'] = 'no'
                    
                    # Extract review URL - comprehensive extraction with debugging
                    try:
                        review_id = None
                        
                        # DEBUG: First check what we're working with
                        if idx <= 2:  # Only debug first 2 reviews
                            debug_info = await review_elem.evaluate("""
                                (element) => {
                                    return {
                                        hasDataReviewId: !!element.getAttribute('data-review-id'),
                                        dataReviewId: element.getAttribute('data-review-id'),
                                        className: element.className,
                                        tagName: element.tagName,
                                        allAttributes: Array.from(element.attributes).map(a => `${a.name}=${a.value}`),
                                        hasLinks: element.querySelectorAll('a').length,
                                        hasButtons: element.querySelectorAll('button').length
                                    }
                                }
                            """)
                            print(f"\n🔍 DEBUG Review {idx}: {debug_info}")
                        
                        # Use comprehensive JavaScript extraction
                        review_id = await review_elem.evaluate("""
                            (element) => {
                                // Method 1: Direct data-review-id on this element
                                let reviewId = element.getAttribute('data-review-id');
                                if (reviewId) return reviewId;
                                
                                // Method 2: Check parent and grandparent
                                let parent = element.parentElement;
                                if (parent && parent.getAttribute('data-review-id')) {
                                    return parent.getAttribute('data-review-id');
                                }
                                
                                let grandparent = parent ? parent.parentElement : null;
                                if (grandparent && grandparent.getAttribute('data-review-id')) {
                                    return grandparent.getAttribute('data-review-id');
                                }
                                
                                // Method 3: Search ALL descendants with data-review-id
                                const allWithReviewId = element.querySelectorAll('[data-review-id]');
                                if (allWithReviewId.length > 0) {
                                    return allWithReviewId[0].getAttribute('data-review-id');
                                }
                                
                                // Method 4: Look for data-feature-id or similar
                                const dataFeatureId = element.querySelector('[data-feature-id]');
                                if (dataFeatureId) {
                                    const fid = dataFeatureId.getAttribute('data-feature-id');
                                    if (fid && fid.includes('review')) {
                                        return fid;
                                    }
                                }
                                
                                // Method 5: Search in ALL buttons and links
                                const allLinks = element.querySelectorAll('a, button, [role="button"]');
                                for (let link of allLinks) {
                                    // Check data-review-id
                                    const rid = link.getAttribute('data-review-id');
                                    if (rid) return rid;
                                    
                                    // Check href
                                    const href = link.getAttribute('href') || '';
                                    if (href.includes('reviewId=')) {
                                        const match = href.match(/reviewId=([^&]+)/);
                                        if (match) return match[1];
                                    }
                                    
                                    // Check data-href
                                    const dataHref = link.getAttribute('data-href') || '';
                                    if (dataHref.includes('reviewId=')) {
                                        const match = dataHref.match(/reviewId=([^&]+)/);
                                        if (match) return match[1];
                                    }
                                    
                                    // Check jsaction
                                    const jsaction = link.getAttribute('jsaction') || '';
                                    if (jsaction.includes('review')) {
                                        // Try to extract ID from jsaction
                                        const idMatch = jsaction.match(/review[^;]*[;:]([A-Za-z0-9_-]{20,})/);
                                        if (idMatch) return idMatch[1];
                                    }
                                }
                                
                                // Method 6: Look for any attribute with long base64-like string
                                const allElements = element.querySelectorAll('*');
                                for (let el of allElements) {
                                    for (let attr of el.attributes) {
                                        const val = attr.value;
                                        // Look for ChdD... pattern (Google review ID pattern)
                                        if (val.startsWith('ChZD') || val.startsWith('Chd') || val.startsWith('ChdD')) {
                                            if (val.length > 20 && val.length < 200) {
                                                return val;
                                            }
                                        }
                                    }
                                }
                                
                                return null;
                            }
                        """)
                        
                        # Build the review URL
                        if review_id:
                            # Get the base place URL (without query parameters)
                            current_url = self.page.url
                            base_url = current_url.split('?')[0]
                            
                            # Create review URL with reviewId parameter
                            review_data['review_url'] = f"{base_url}?reviewId={review_id}"
                            if idx <= 2:
                                print(f"\n✅ Review {idx} ID: {review_id[:30]}...")
                        else:
                            # Fallback: use the place URL
                            review_data['review_url'] = self.page.url
                            print(f"\n⚠️ Could not extract review ID for review {idx}")
                    except Exception as url_error:
                        print(f"\n⚠️ Error extracting review URL: {url_error}")
                        review_data['review_url'] = self.page.url
                    
                    # DEDUPLICATION: Create unique key for this review
                    review_key = (
                        review_data.get('reviewer_name', ''),
                        review_data.get('review_text', '')[:50]  # First 50 chars of review text
                    )
                    
                    # Skip if we've already seen this review
                    if review_key in seen_reviewers:
                        print(f"\n  ⏭️  Skipping duplicate review from {review_data.get('reviewer_name', 'Unknown')}")
                        continue
                    
                    seen_reviewers.add(review_key)
                    reviews.append(review_data)
                    
                    # Call the callback function if provided (for real-time processing)
                    if on_review_callback:
                        try:
                            print(f"\n📤 Calling webhook callback for review {len(reviews)}/{total}")
                            await on_review_callback(review_data, len(reviews), total)
                        except Exception as callback_error:
                            print(f"\n⚠️ Callback error: {callback_error}")
                    
                except Exception as e:
                    print(f"\n⚠️ Error extracting review {idx}: {e}")
                    continue
            
            duplicates_removed = total - len(reviews)
            print(f"\n✓ Successfully extracted {len(reviews)} unique reviews (removed {duplicates_removed} duplicates)")
            return reviews
            
        except Exception as e:
            print(f"❌ Error in review extraction: {e}")
            return reviews

    async def scrape(self, maps_url: str, max_reviews: Optional[int] = None, on_review_callback=None) -> Dict:
        """
        Main scraping function for reviews.
        
        Args:
            maps_url: Google Maps place URL
            max_reviews: Maximum number of reviews to scrape (None = all)
            on_review_callback: Optional async callback function called after each review is extracted
            
        Returns:
            Dictionary containing:
                - place_name: Name of the business/place
                - place_url: Google Maps URL
                - reviews: List of review dictionaries
        """
        reviews = []
        place_name = None
        place_url = maps_url
        
        # Force English language by adding hl=en parameter to URL
        if '?' in maps_url:
            if 'hl=' not in maps_url:
                maps_url = maps_url + '&hl=en'
        else:
            maps_url = maps_url + '?hl=en'
        
        # Pre-resolve short URLs (maps.app.goo.gl) to avoid redirect issues through proxies
        if 'goo.gl' in maps_url or 'maps.app' in maps_url:
            print(f"🔗 Resolving short URL: {maps_url}")
            try:
                import httpx as _httpx
                import urllib.parse as _urlparse
                async with _httpx.AsyncClient(follow_redirects=True, timeout=15) as client:
                    resp = await client.head(maps_url)
                    resolved_url = str(resp.url)
                    if resolved_url != maps_url and 'google.com/maps' in resolved_url:
                        # Clean tracking parameters that may cause blocks
                        parsed = _urlparse.urlparse(resolved_url)
                        params = _urlparse.parse_qs(parsed.query)
                        # Remove tracking/fingerprinting params
                        tracking_params = ['g_ep', 'skid', 'entry', 'authuser', 'g_st', 'shorturl']
                        for tp in tracking_params:
                            params.pop(tp, None)
                        clean_query = _urlparse.urlencode(params, doseq=True)
                        resolved_url = _urlparse.urlunparse(parsed._replace(query=clean_query))
                        print(f"✅ Resolved & cleaned URL: {resolved_url}")
                        maps_url = resolved_url
                        # Re-add hl=en if needed
                        if 'hl=' not in maps_url:
                            maps_url = maps_url + ('&' if '?' in maps_url else '?') + 'hl=en'
                    else:
                        print(f"⚠️ URL resolved to: {resolved_url} (keeping original)")
            except Exception as e:
                print(f"⚠️ Could not pre-resolve short URL: {e} (will try navigating directly)")
        
        max_retries = 3  # 1 direct + 2 with proxy as fallback
        for attempt in range(1, max_retries + 1):
            try:
                # Strategy: try direct connection FIRST, then proxy if blocked
                if attempt == 1:
                    # First attempt: NO proxy (direct connection - fastest & most reliable)
                    print("\n🔗 Attempt 1: Direct connection (no proxy)...")
                    original_use_proxies = ScraperConfig.USE_PROXIES
                    ScraperConfig.USE_PROXIES = False
                    await self._setup_browser()
                    ScraperConfig.USE_PROXIES = original_use_proxies
                else:
                    # Subsequent attempts: try with proxy (in case direct is blocked/captcha)
                    print(f"\n🔗 Attempt {attempt}: Trying with proxy...")
                    await self._setup_browser()
                
                # Navigate to URL with retry
                # Direct connection gets longer timeout, proxy gets shorter
                nav_timeout = 60000 if not self._current_proxy else 30000
                print(f"🌐 Navigating to Google Maps place... (attempt {attempt}/{max_retries}, timeout={nav_timeout//1000}s, proxy={'yes' if self._current_proxy else 'NO'})")
                try:
                    await self.page.goto(maps_url, wait_until='domcontentloaded', timeout=nav_timeout)
                except Exception as nav_error:
                    error_msg = str(nav_error).lower()
                    if 'timeout' in error_msg or 'net::' in error_msg:
                        print(f"⚠️ Navigation failed (proxy may be blocked/slow): {nav_error}")
                        # Try to save whatever loaded
                        try:
                            await self._save_debug_page(f'nav_failed_attempt{attempt}')
                        except:
                            print("   Could not save debug page after nav failure")
                        if self._current_proxy:
                            self._used_proxies.add(self._current_proxy)
                            print(f"🔄 Blacklisting proxy and retrying with a different one...")
                        await self.cleanup()
                        if attempt < max_retries:
                            await asyncio.sleep(3)
                            continue
                        else:
                            raise
                    else:
                        raise
                
                await asyncio.sleep(4)
                
                # === DEBUG: Save page source right after navigation ===
                await self._save_debug_page(f'after_navigation_attempt{attempt}')
                
                # Handle consent first
                await self._handle_consent_dialog()
                await asyncio.sleep(2)
                
                # Check for CAPTCHA / block page
                is_blocked = await self._check_for_captcha()
                if is_blocked:
                    print(f"🚫 CAPTCHA/block detected!")
                    await self._save_debug_page(f'captcha_detected_attempt{attempt}')
                    if self._current_proxy:
                        self._used_proxies.add(self._current_proxy)
                        print(f"🔄 Blacklisting proxy and retrying...")
                    await self.cleanup()
                    if attempt < max_retries:
                        await asyncio.sleep(5)
                        continue
                    else:
                        print("❌ All retries exhausted due to CAPTCHA/blocks")
                        raise Exception("Google CAPTCHA/block detected after all retries")
                
                # Get current URL (after redirects)
                current_url = self.page.url
                place_url = current_url
                print(f"📍 Current URL: {current_url}")
            
                # Extract place name
                try:
                    place_name = await self.page.evaluate("""
                        () => {
                            // Try multiple selectors for place name
                            const selectors = [
                                'h1',
                                'h1[class*="fontHeadline"]',
                                '[role="main"] h1',
                                'div[role="main"] h1'
                            ];
                            
                            for (let selector of selectors) {
                                const elem = document.querySelector(selector);
                                if (elem && elem.innerText) {
                                    return elem.innerText.trim();
                                }
                            }
                            return null;
                        }
                    """)
                    if place_name:
                        print(f"🏪 Place Name: {place_name}")
                except Exception as e:
                    print(f"⚠️ Could not extract place name: {e}")
                
                # Take initial debug snapshot
                await self._save_debug_page(f'before_reviews_click_attempt{attempt}')
                
                # CRITICAL FIX: Use JavaScript to directly click the Reviews tab
                print("🔍 Using JavaScript to find and click Reviews tab...")
                reviews_opened = await self._force_open_reviews_with_js()
                
                # Debug snapshot after reviews click attempt
                await self._save_debug_page(f'after_reviews_click_attempt{attempt}')
                
                if not reviews_opened:
                    print("⚠️ Could not open reviews tab, trying fallback method...")
                    # Fallback: Try the old click method
                    reviews_opened = await self._click_reviews_tab()
                
                if not reviews_opened:
                    # Last resort: Force reload with hl=en to ensure English interface
                    print("🔄 Retrying with forced English language reload...")
                    current = self.page.url
                    # Strip any existing hl= param and add hl=en
                    import urllib.parse
                    parsed = urllib.parse.urlparse(current)
                    params = urllib.parse.parse_qs(parsed.query)
                    params['hl'] = ['en']
                    new_query = urllib.parse.urlencode(params, doseq=True)
                    english_url = urllib.parse.urlunparse(parsed._replace(query=new_query))
                    
                    await self.page.goto(english_url, wait_until='domcontentloaded', timeout=60000)
                    await asyncio.sleep(5)
                    await self._handle_consent_dialog()
                    await asyncio.sleep(2)
                    
                    reviews_opened = await self._force_open_reviews_with_js()
                    if not reviews_opened:
                        reviews_opened = await self._click_reviews_tab()
                
                # Final debug snapshot before extraction
                await self._save_debug_page(f'before_extraction_attempt{attempt}')
                
                # Scroll to load more reviews
                await self._scroll_reviews(max_reviews)
                
                # Expand all "Read more" / "More" buttons on individual reviews
                try:
                    expanded = await self.page.evaluate("""
                        () => {
                            let count = 0;
                            // Click all "More" / "Read more" / "Mehr" expand buttons on reviews
                            const expandKeywords = ['more', 'mehr', 'plus', 'm\u00e1s', 'altro', 'daha', '\u0627\u0644\u0645\u0632\u064a\u062f'];
                            const buttons = document.querySelectorAll('button.w8nwRe, button.M77dve, button[jsaction*="review"], button[aria-expanded="false"]');
                            buttons.forEach(btn => {
                                const text = (btn.innerText || '').toLowerCase().trim();
                                if (expandKeywords.some(kw => text.includes(kw)) || text === '' || btn.classList.contains('w8nwRe')) {
                                    btn.click();
                                    count++;
                                }
                            });
                            return count;
                        }
                    """)
                    if expanded > 0:
                        print(f"📖 Expanded {expanded} review texts")
                        await asyncio.sleep(2)
                except:
                    pass
                
                # Extract reviews
                reviews = await self._extract_reviews(max_reviews, on_review_callback)
                
                # Success - break out of retry loop
                break
                
            except Exception as e:
                print(f"❌ Error during scraping (attempt {attempt}/{max_retries}): {e}")
                # Try to save debug page on error
                try:
                    if self.page:
                        await self._save_debug_page(f'error_attempt{attempt}')
                except:
                    pass
                await self.cleanup()
                if attempt < max_retries:
                    if self._current_proxy:
                        self._used_proxies.add(self._current_proxy)
                    print(f"🔄 Retrying with different proxy...")
                    await asyncio.sleep(3)
                    continue
                else:
                    raise
            
            finally:
                await self.cleanup()
        
        return {
            'place_name': place_name,
            'place_url': place_url,
            'reviews': reviews
        }

    async def cleanup(self):
        """Close browser and cleanup resources."""
        try:
            if self.context:
                await self.context.close()
                self.context = None
        except:
            pass
        try:
            if self.browser:
                await self.browser.close()
                self.browser = None
        except:
            pass
        self.page = None


async def scrape_google_maps_reviews(maps_url: str, headless: bool = True, max_reviews: Optional[int] = None, on_review_callback=None) -> Dict:
    """
    Convenience function to scrape Google Maps reviews.
    
    Args:
        maps_url: Google Maps place URL
        headless: Run browser in headless mode
        max_reviews: Maximum number of reviews to scrape
        on_review_callback: Optional async callback function called after each review
        
    Returns:
        Dictionary containing place_name, place_url, and reviews list
    """
    scraper = GoogleMapsReviewsScraper(headless=headless)
    return await scraper.scrape(maps_url, max_reviews, on_review_callback)
