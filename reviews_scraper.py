#!/usr/bin/env python3
"""
Google Maps Reviews Scraper - Clean rebuild
Extracts reviews from a specific Google Maps place using Playwright.
"""

import asyncio
import json
import os
import random
import re
from datetime import datetime
from typing import List, Dict, Optional

from playwright.async_api import async_playwright, Page, Browser, BrowserContext
from config import proxy_config, ScraperConfig

# Import stealth plugin (supports both v1.x and v2.x)
STEALTH_AVAILABLE = False
_stealth_instance = None
try:
    from playwright_stealth import Stealth
    _stealth_instance = Stealth()
    STEALTH_AVAILABLE = True
except ImportError:
    try:
        from playwright_stealth import stealth_async
        STEALTH_AVAILABLE = True
    except ImportError:
        print("⚠️ playwright-stealth not installed. Continuing without stealth.")

# Debug directory
DEBUG_DIR = "output/debug"
os.makedirs(DEBUG_DIR, exist_ok=True)


class GoogleMapsReviewsScraper:
    """Scraper for Google Maps reviews."""

    def __init__(self, headless: bool = True):
        self.headless = headless
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.playwright = None
        self._current_proxy = None

    # ──────────────────────────────────────────────
    #  Browser setup
    # ──────────────────────────────────────────────

    async def _setup_browser(self, use_proxy: bool = False):
        """Launch browser with stealth config."""
        if not self.playwright:
            self.playwright = await async_playwright().start()

        launch_opts = {
            "headless": self.headless,
            "args": [
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled",
            ],
        }

        self._current_proxy = None
        if use_proxy and ScraperConfig.USE_PROXIES and proxy_config.proxies:
            proxy_url = random.choice(proxy_config.proxies)
            proxy_dict = proxy_config._parse_proxy_url(proxy_url)
            if proxy_dict:
                launch_opts["proxy"] = proxy_dict
                self._current_proxy = proxy_url
                print(f"🌐 Using proxy: {proxy_dict['server']}")

        if not self._current_proxy:
            print("🔗 Direct connection (no proxy)")

        self.browser = await self.playwright.chromium.launch(**launch_opts)
        self.context = await self.browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent=ScraperConfig.get_random_user_agent(),
            locale="en-US",
        )

        # Load Google cookies
        try:
            from pathlib import Path
            cfile = Path("google_cookies.json")
            if cfile.exists() and cfile.stat().st_size > 10:
                with open(cfile) as f:
                    cookies = json.load(f)
                if cookies:
                    await self.context.add_cookies(cookies)
                    print(f"✅ Loaded {len(cookies)} cookies")
        except Exception as e:
            print(f"⚠️ Cookies error: {e}")

        self.page = await self.context.new_page()

        # Apply stealth
        if STEALTH_AVAILABLE:
            try:
                if _stealth_instance:
                    await _stealth_instance.apply_stealth_async(self.page)
                else:
                    await stealth_async(self.page)
                print("✓ Stealth mode enabled")
            except Exception as e:
                print(f"⚠️ Stealth failed: {e}")

        # Extra anti-detection
        await self.page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => false });
            Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
        """)

    # ──────────────────────────────────────────────
    #  Debug helpers
    # ──────────────────────────────────────────────

    async def _debug_save(self, label: str):
        """Save screenshot + HTML for debugging."""
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        base = os.path.join(DEBUG_DIR, f"{ts}_{label}")
        try:
            html = await self.page.content()
            with open(f"{base}.html", "w", encoding="utf-8") as f:
                f.write(html)
            await self.page.screenshot(path=f"{base}.png", full_page=True)
            url = self.page.url
            title = await self.page.title()
            print(f"📸 Debug [{label}]: {url[:80]} | title={title[:40]} | html={len(html)}b")
        except Exception as e:
            print(f"⚠️ Debug save failed: {e}")

    # ──────────────────────────────────────────────
    #  URL resolution
    # ──────────────────────────────────────────────

    async def _resolve_url(self, url: str) -> str:
        """Resolve short URL and clean tracking params."""
        if "goo.gl" not in url and "maps.app" not in url:
            return url

        print(f"🔗 Resolving short URL...")
        try:
            import httpx
            import urllib.parse
            async with httpx.AsyncClient(follow_redirects=True, timeout=15) as client:
                resp = await client.head(url)
                resolved = str(resp.url)
                if "google.com/maps" in resolved:
                    # Strip tracking params
                    parsed = urllib.parse.urlparse(resolved)
                    params = urllib.parse.parse_qs(parsed.query)
                    for tp in ["g_ep", "skid", "entry", "authuser", "g_st", "shorturl"]:
                        params.pop(tp, None)
                    clean = urllib.parse.urlencode(params, doseq=True)
                    resolved = urllib.parse.urlunparse(parsed._replace(query=clean))
                    print(f"✅ Resolved: {resolved[:100]}...")
                    return resolved
        except Exception as e:
            print(f"⚠️ Could not resolve: {e}")
        return url

    # ──────────────────────────────────────────────
    #  Navigation & checks
    # ──────────────────────────────────────────────

    async def _navigate(self, url: str, timeout: int = 60000) -> bool:
        """Navigate to URL. Returns True on success."""
        try:
            await self.page.goto(url, wait_until="domcontentloaded", timeout=timeout)
            await asyncio.sleep(3)
            return True
        except Exception as e:
            print(f"⚠️ Navigation failed: {e}")
            try:
                await self._debug_save("nav_failed")
            except:
                pass
            return False

    async def _is_blocked(self) -> bool:
        """Check for CAPTCHA/block."""
        try:
            content = await self.page.content()
            url = self.page.url
            lower = content.lower()

            if len(content) < 500:
                print(f"🚫 Page too small ({len(content)}b) - likely blocked")
                return True

            indicators = [
                "recaptcha", "g-recaptcha", "captcha",
                "unusual traffic", "automated queries",
                "sorry/index", "are not a robot",
            ]
            for ind in indicators:
                if ind in lower or ind in url.lower():
                    print(f"🚫 Block detected: '{ind}'")
                    return True
            return False
        except:
            return False

    async def _handle_consent(self):
        """Click cookie consent buttons."""
        for text in ["Accept all", "I agree", "Reject all"]:
            try:
                btn = await self.page.wait_for_selector(
                    f'button:has-text("{text}")', timeout=2000
                )
                if btn:
                    await btn.click()
                    await asyncio.sleep(1)
                    return
            except:
                continue

    # ──────────────────────────────────────────────
    #  Click the Reviews tab
    # ──────────────────────────────────────────────

    async def _open_reviews_tab(self) -> bool:
        """Find and click the Reviews tab. Returns True on success."""
        print("🔍 Looking for Reviews tab...")

        # The JS finds tabs and clicks the right one
        result = await self.page.evaluate("""
            () => {
                const reviewKW = [
                    'review', 'rezension', 'bewertung', 'avis',
                    'rese\\u00f1', 'opiniones', 'recens', 'valutazion',
                    'avalia', 'yorum', '\\u043e\\u0442\\u0437\\u044b\\u0432',
                    '\\u0645\\u0631\\u0627\\u062c\\u0639', '\\u062a\\u0642\\u064a\\u064a\\u0645',
                    '\\u30ec\\u30d3\\u30e5\\u30fc', '\\ub9ac\\ubdf0', '\\u8bc4\\u8bba',
                ];
                const excludeKW = [
                    'overview', 'about', 'menu', 'speisekarte', 'karte',
                    'photos', 'fotos', 'bilder', 'updates', 'contact',
                    'write', '\\u0643\\u062a\\u0627\\u0628\\u0629', 'schreiben',
                ];

                function isReview(text, aria) {
                    const c = (text + ' ' + aria).toLowerCase();
                    if (excludeKW.some(k => c.includes(k))) return false;
                    return reviewKW.some(k => c.includes(k));
                }

                // Method 1: role="tab" buttons
                const tabs = Array.from(document.querySelectorAll('button[role="tab"]'));
                for (let tab of tabs) {
                    const t = (tab.innerText || '').toLowerCase();
                    const a = (tab.getAttribute('aria-label') || '').toLowerCase();
                    if (isReview(t, a)) {
                        tab.click();
                        return {ok: true, method: 'tab', text: tab.innerText.trim().substring(0, 40)};
                    }
                }

                // Method 2: tab with number that's not excluded
                for (let tab of tabs) {
                    const t = (tab.innerText || '');
                    const a = (tab.getAttribute('aria-label') || '').toLowerCase();
                    const c = (t + ' ' + a).toLowerCase();
                    if (excludeKW.some(k => c.includes(k))) continue;
                    if (/\\d+/.test(t)) {
                        tab.click();
                        return {ok: true, method: 'tab_num', text: t.trim().substring(0, 40)};
                    }
                }

                // Method 3: any button matching review keywords
                const btns = Array.from(document.querySelectorAll('button'));
                for (let btn of btns) {
                    const t = (btn.innerText || '').trim();
                    const a = (btn.getAttribute('aria-label') || '');
                    if (t.length < 40 && !t.includes('\\n') && isReview(t, a)) {
                        btn.click();
                        return {ok: true, method: 'btn', text: t.substring(0, 40)};
                    }
                }

                // Debug info
                const tabInfo = tabs.map(t => (t.innerText || '').replace(/\\n/g, ' ').substring(0, 30));
                return {ok: false, tabs: tabInfo};
            }
        """)

        print(f"  Tab result: {result}")
        if result.get("ok"):
            print(f"✓ Opened reviews: {result.get('method')} - '{result.get('text')}'")
            await asyncio.sleep(4)
            return True

        print("⚠️ Could not find Reviews tab")
        return False

    # ──────────────────────────────────────────────
    #  Scroll reviews
    # ──────────────────────────────────────────────

    async def _count_reviews(self) -> int:
        """Count visible review elements."""
        return await self.page.evaluate("""
            () => {
                let r = document.querySelectorAll('div[data-review-id]');
                if (r.length === 0) r = document.querySelectorAll('div.jftiEf');
                return r.length;
            }
        """)

    async def _scroll_reviews(self, max_reviews: Optional[int] = None) -> int:
        """Scroll to load reviews. Returns count of visible reviews."""
        print("📜 Scrolling to load reviews...")
        await asyncio.sleep(2)

        count = await self._count_reviews()
        print(f"  Initial reviews visible: {count}")

        if count == 0:
            print("⚠️ No review elements found — nothing to scroll")
            return 0

        # Find the scrollable container by walking up from a review element
        container = await self.page.evaluate_handle("""
            () => {
                const review = document.querySelector('div[data-review-id]')
                                || document.querySelector('div.jftiEf');
                if (!review) return null;

                // Walk up to find scrollable parent
                let el = review.parentElement;
                while (el && el !== document.body) {
                    const s = window.getComputedStyle(el);
                    if ((s.overflowY === 'auto' || s.overflowY === 'scroll')
                        && el.scrollHeight > el.clientHeight + 50) {
                        return el;
                    }
                    el = el.parentElement;
                }

                // Fallback: .m6QErb panels
                const panels = document.querySelectorAll('.m6QErb');
                for (let p of panels) {
                    if (p.scrollHeight > p.clientHeight + 50
                        && (p.querySelector('div[data-review-id]') || p.querySelector('div.jftiEf'))) {
                        return p;
                    }
                }

                return null;
            }
        """)

        has_container = await self.page.evaluate("(el) => el !== null", container)
        if not has_container:
            print("⚠️ No scroll container found — will try keyboard scrolling")

        no_change = 0
        scroll_num = 0
        prev_count = count

        while True:
            scroll_num += 1

            # Check if we have enough
            if max_reviews and count >= max_reviews:
                print(f"  ✓ Reached target: {count}/{max_reviews}")
                break

            # Stop conditions
            if no_change >= 6:
                at_bottom = await self.page.evaluate("""
                    (el) => {
                        if (!el) return true;
                        return el.scrollTop + el.clientHeight >= el.scrollHeight - 30;
                    }
                """, container)
                if at_bottom:
                    print(f"  ✓ Reached end of reviews ({count} total)")
                    break
                if no_change >= 10:
                    print(f"  ⚠️ Stuck at {count} reviews after {no_change} unchanged scrolls")
                    break

            # Scroll the container
            if has_container:
                await self.page.evaluate("(el) => { if (el) el.scrollTop += 800; }", container)
            else:
                await self.page.keyboard.press("End")

            await asyncio.sleep(1.5)

            # Also scroll the last review into view as backup
            await self.page.evaluate("""
                () => {
                    let r = document.querySelectorAll('div[data-review-id]');
                    if (r.length === 0) r = document.querySelectorAll('div.jftiEf');
                    if (r.length > 0) r[r.length - 1].scrollIntoView({behavior: 'instant', block: 'end'});
                }
            """)
            await asyncio.sleep(1)

            count = await self._count_reviews()

            if count == prev_count:
                no_change += 1
                # On 3rd stuck attempt, try keyboard + page down
                if no_change == 3:
                    await self.page.keyboard.press("End")
                    await asyncio.sleep(0.5)
                    await self.page.keyboard.press("PageDown")
                    await asyncio.sleep(1)
                    count = await self._count_reviews()
            else:
                no_change = 0

            if scroll_num % 5 == 0 or count != prev_count:
                print(f"  Scroll #{scroll_num}: {count} reviews (stuck={no_change})")

            prev_count = count

        print(f"✓ Scrolling done: {count} reviews loaded")
        return count

    # ──────────────────────────────────────────────
    #  Expand review texts ("More" buttons)
    # ──────────────────────────────────────────────

    async def _expand_reviews(self):
        """Click all 'More'/'Read more' buttons to show full review text."""
        expanded = await self.page.evaluate("""
            () => {
                let n = 0;
                // Google Maps uses w8nwRe class for "More" buttons inside reviews
                const btns = document.querySelectorAll('button.w8nwRe, button.M77dve');
                btns.forEach(b => { b.click(); n++; });
                return n;
            }
        """)
        if expanded:
            print(f"📖 Expanded {expanded} review texts")
            await asyncio.sleep(1)

    # ──────────────────────────────────────────────
    #  Extract reviews
    # ──────────────────────────────────────────────

    async def _extract_reviews(self, max_reviews: Optional[int] = None, on_review_callback=None) -> List[Dict]:
        """Extract review data from the page."""
        reviews = []
        seen = set()

        elements = await self.page.query_selector_all("div[data-review-id]")
        if not elements:
            elements = await self.page.query_selector_all("div.jftiEf")
        if not elements:
            print("⚠️ No review elements to extract")
            return reviews

        total = min(len(elements), max_reviews) if max_reviews else len(elements)
        print(f"📊 Extracting {total} reviews...")

        for idx, el in enumerate(elements[:total], 1):
            try:
                data = await self.page.evaluate("""
                    (el) => {
                        // Reviewer name
                        const nameEl = el.querySelector('.d4r55')
                                     || el.querySelector('.WNxzHc a');
                        const name = nameEl ? nameEl.innerText.trim() : '';

                        // Rating
                        let rating = 0;
                        const starEl = el.querySelector('span[role="img"]');
                        if (starEl) {
                            const aria = starEl.getAttribute('aria-label') || '';
                            const m = aria.match(/(\\d)/);
                            if (m) rating = parseInt(m[1]);
                        }

                        // Date
                        const dateEl = el.querySelector('.rsqaWe');
                        const date = dateEl ? dateEl.innerText.trim() : '';

                        // Review text
                        const fullText = el.querySelector('.wiI7pd');
                        const text = fullText ? fullText.innerText.trim() : '';

                        // Pictures
                        const pics = el.querySelectorAll('button.Tya61d, div.KtCyie button');
                        const hasPics = pics.length > 0 ? 'yes' : 'no';

                        // Company reply
                        const replyEl = el.querySelector('.CDe7pd');
                        const reply = replyEl ? replyEl.innerText.trim() : 'no';

                        // Review URL
                        const reviewId = el.getAttribute('data-review-id') || '';

                        return { name, rating, date, text, hasPics, reply, reviewId };
                    }
                """, el)

                name = data.get("name", "")
                if not name or name in seen:
                    continue
                seen.add(name)

                review = {
                    "reviewer_name": name,
                    "review_date": data.get("date", ""),
                    "rating": data.get("rating", 0),
                    "review_text": data.get("text", ""),
                    "pictures": data.get("hasPics", "no"),
                    "company_reply": data.get("reply", "no"),
                    "review_url": data.get("reviewId", ""),
                }
                reviews.append(review)

                if on_review_callback:
                    try:
                        await on_review_callback(review, len(reviews), total)
                    except Exception as cbe:
                        print(f"⚠️ Callback error: {cbe}")

            except Exception as e:
                print(f"⚠️ Error extracting review {idx}: {e}")
                continue

        print(f"✓ Extracted {len(reviews)} unique reviews")
        return reviews

    # ──────────────────────────────────────────────
    #  Main scrape method
    # ──────────────────────────────────────────────

    async def scrape(self, maps_url: str, max_reviews: Optional[int] = None, on_review_callback=None) -> Dict:
        """
        Scrape reviews from a Google Maps place URL.

        Returns dict with place_name, place_url, reviews list.
        """
        place_name = None
        place_url = maps_url

        # Resolve short URL
        maps_url = await self._resolve_url(maps_url)

        # Add hl=en
        sep = "&" if "?" in maps_url else "?"
        if "hl=" not in maps_url:
            maps_url += f"{sep}hl=en"

        # Attempt strategy: direct first, then proxy
        attempts = [
            {"label": "direct", "use_proxy": False, "timeout": 60000},
            {"label": "proxy-1", "use_proxy": True, "timeout": 30000},
            {"label": "proxy-2", "use_proxy": True, "timeout": 30000},
        ]

        for i, attempt in enumerate(attempts, 1):
            label = attempt["label"]
            print(f"\n{'='*50}")
            print(f"🔄 Attempt {i}/{len(attempts)} ({label})")
            print(f"{'='*50}")

            try:
                await self._setup_browser(use_proxy=attempt["use_proxy"])

                # Navigate
                print(f"🌐 Navigating... (timeout={attempt['timeout']//1000}s)")
                ok = await self._navigate(maps_url, timeout=attempt["timeout"])
                if not ok:
                    await self.cleanup()
                    continue

                # Check blocked
                if await self._is_blocked():
                    await self._debug_save(f"blocked_{label}")
                    await self.cleanup()
                    continue

                # Consent
                await self._handle_consent()
                await asyncio.sleep(2)

                # Debug save after page loads
                await self._debug_save(f"loaded_{label}")

                # Get place name
                place_name = await self.page.evaluate("""
                    () => {
                        const h = document.querySelector('h1');
                        return h ? h.innerText.trim() : null;
                    }
                """)
                if place_name:
                    print(f"🏪 Place: {place_name}")

                place_url = self.page.url

                # Click Reviews tab
                if not await self._open_reviews_tab():
                    # Retry with English reload
                    print("🔄 Retrying with hl=en...")
                    current = self.page.url
                    import urllib.parse
                    parsed = urllib.parse.urlparse(current)
                    params = urllib.parse.parse_qs(parsed.query)
                    params["hl"] = ["en"]
                    new_q = urllib.parse.urlencode(params, doseq=True)
                    en_url = urllib.parse.urlunparse(parsed._replace(query=new_q))
                    await self._navigate(en_url)
                    await self._handle_consent()
                    await asyncio.sleep(2)
                    if not await self._open_reviews_tab():
                        await self._debug_save(f"no_tab_{label}")
                        await self.cleanup()
                        continue

                await self._debug_save(f"reviews_tab_{label}")

                # Wait for reviews to appear
                await asyncio.sleep(3)
                initial = await self._count_reviews()
                print(f"  Initial review count: {initial}")

                if initial == 0:
                    await asyncio.sleep(5)
                    initial = await self._count_reviews()
                    if initial == 0:
                        print("⚠️ No reviews appeared after waiting")
                        await self._debug_save(f"no_reviews_{label}")
                        await self.cleanup()
                        continue

                # Scroll to load more
                await self._scroll_reviews(max_reviews)

                # Expand review texts
                await self._expand_reviews()

                # Extract
                reviews = await self._extract_reviews(max_reviews, on_review_callback)

                await self._debug_save(f"done_{label}")

                return {
                    "place_name": place_name,
                    "place_url": place_url,
                    "reviews": reviews,
                }

            except Exception as e:
                print(f"❌ Attempt {i} error: {e}")
                try:
                    await self._debug_save(f"error_{label}")
                except:
                    pass
                await self.cleanup()
                continue

            finally:
                await self.cleanup()

        # All attempts failed
        print("❌ All attempts failed")
        return {
            "place_name": place_name,
            "place_url": place_url,
            "reviews": [],
        }

    # ──────────────────────────────────────────────
    #  Cleanup
    # ──────────────────────────────────────────────

    async def cleanup(self):
        """Close browser resources."""
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


# ──────────────────────────────────────────────
#  Convenience function (used by api.py)
# ──────────────────────────────────────────────

async def scrape_google_maps_reviews(
    maps_url: str,
    headless: bool = True,
    max_reviews: Optional[int] = None,
    on_review_callback=None,
) -> Dict:
    """Convenience function to scrape Google Maps reviews."""
    scraper = GoogleMapsReviewsScraper(headless=headless)
    return await scraper.scrape(maps_url, max_reviews, on_review_callback)
