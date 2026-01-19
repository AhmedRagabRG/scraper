#!/usr/bin/env python3
"""
Google Maps Reviews Scraper
Extracts reviews from a specific Google Maps place
"""

import asyncio
import random
import re
from typing import List, Dict, Optional
from playwright.async_api import async_playwright, Page, Browser, BrowserContext


class GoogleMapsReviewsScraper:
    """Scraper for Google Maps reviews."""

    def __init__(self, headless: bool = True):
        self.headless = headless
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None

    async def _setup_browser(self):
        """Initialize browser with stealth configurations."""
        playwright = await async_playwright().start()
        
        self.browser = await playwright.chromium.launch(
            headless=self.headless,
            args=[
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-blink-features=AutomationControlled',
            ]
        )

        self.context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            locale='en-US',
            extra_http_headers={
                'Accept-Language': 'en-US,en;q=0.9',
            },
            geolocation={'latitude': 40.7128, 'longitude': -74.0060},  # New York
            permissions=['geolocation'],
        )

        self.page = await self.context.new_page()

        # Stealth JavaScript
        await self.page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => false,
            });
            
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en'],
            });
        """)

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
            result = await self.page.evaluate("""
                () => {
                    // Find all buttons
                    const buttons = Array.from(document.querySelectorAll('button'));
                    
                    // Method 1: Look for tabs specifically (role="tab")
                    const tabs = buttons.filter(btn => btn.getAttribute('role') === 'tab');
                    if (tabs.length > 0) {
                        for (let tab of tabs) {
                            const text = (tab.innerText || tab.textContent || '').toLowerCase();
                            const ariaLabel = (tab.getAttribute('aria-label') || '').toLowerCase();
                            
                            if (text.includes('review') || text.includes('مراجع') || 
                                ariaLabel.includes('review') || ariaLabel.includes('مراجع')) {
                                console.log('Found Reviews tab:', tab.innerText);
                                tab.click();
                                return { success: true, method: 'reviews_tab', text: tab.innerText };
                            }
                        }
                        
                        // If no review tab found, click second tab (usually Reviews)
                        if (tabs.length > 1) {
                            console.log('Clicking second tab');
                            tabs[1].click();
                            return { success: true, method: 'second_tab', text: tabs[1].innerText };
                        }
                    }
                    
                    // Method 2: Find button with ONLY "Reviews" text (no names)
                    for (let btn of buttons) {
                        const text = btn.innerText || btn.textContent || '';
                        const ariaLabel = btn.getAttribute('aria-label') || '';
                        
                        // Check if it's JUST the reviews text (no newlines = no user names)
                        if (!text.includes('\\n') && text.trim().length < 30) {
                            const combined = (text + ' ' + ariaLabel).toLowerCase();
                            if ((combined.includes('مراجع') || combined.includes('review')) && 
                                !combined.includes('كتابة') && !combined.includes('write')) {
                                console.log('Found simple reviews button:', text);
                                btn.click();
                                return { success: true, method: 'simple_review_button', text: text };
                            }
                        }
                    }
                    
                    return { success: false, buttons_count: buttons.length, tabs_count: tabs.length };
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
        """Click on the reviews tab - fallback method."""
        try:
            print("⏳ Fallback: Looking for Reviews tab...")
            await asyncio.sleep(2)
            
            # Try to find tabs specifically (role="tab")
            tabs = await self.page.query_selector_all('button[role="tab"]')
            print(f"🔍 Found {len(tabs)} tabs")
            
            if len(tabs) > 1:
                # Usually second tab is Reviews
                second_tab = tabs[1]
                text = await second_tab.inner_text()
                print(f"  Clicking second tab: {text}")
                
                await second_tab.scroll_into_view_if_needed()
                await asyncio.sleep(0.5)
                
                try:
                    await second_tab.click(force=True)
                except:
                    await self.page.evaluate('(btn) => btn.click()', second_tab)
                
                print(f"✓ Clicked second tab")
                await asyncio.sleep(5)
                return True
            
            print("⚠️ Could not find tabs")
            return False
            
        except Exception as e:
            print(f"⚠️ Error in fallback method: {e}")
            return False

    async def _scroll_reviews(self, max_reviews: Optional[int] = None):
        """Scroll through reviews to load more."""
        print("📜 Scrolling through reviews...")
        
        try:
            # Wait for reviews container to load
            await asyncio.sleep(3)
            
            # Find the CORRECT scrollable reviews container (not locations list)
            scrollable_info = await self.page.evaluate("""
                () => {
                    // Find all feed containers
                    const feeds = Array.from(document.querySelectorAll('div[role="feed"]'));
                    console.log('Found', feeds.length, 'feed containers');
                    
                    // The reviews feed usually contains review elements
                    for (let feed of feeds) {
                        const reviewsInFeed = feed.querySelectorAll('div[data-review-id]');
                        if (reviewsInFeed.length > 0) {
                            console.log('Found reviews feed with', reviewsInFeed.length, 'reviews');
                            // Mark this feed for scrolling
                            feed.setAttribute('data-reviews-feed', 'true');
                            feed.style.border = '2px solid red';  // Debug: visual marker
                            return { 
                                found: true, 
                                reviews_count: reviewsInFeed.length,
                                scrollable: feed.scrollHeight > feed.clientHeight
                            };
                        }
                    }
                    
                    // Fallback: find the container parent of reviews
                    const reviews = document.querySelectorAll('div[data-review-id]');
                    if (reviews.length > 0) {
                        let parent = reviews[0].parentElement;
                        while (parent) {
                            if (parent.scrollHeight > parent.clientHeight) {
                                parent.setAttribute('data-reviews-feed', 'true');
                                parent.style.border = '2px solid blue';  // Debug
                                console.log('Found scrollable parent');
                                return { found: true, reviews_count: reviews.length, scrollable: true, method: 'parent' };
                            }
                            parent = parent.parentElement;
                        }
                    }
                    
                    return { found: false, reviews_count: 0 };
                }
            """)
            
            if scrollable_info.get('found'):
                print(f"✓ Found scrollable reviews container ({scrollable_info.get('reviews_count')} reviews visible)")
            else:
                print("⚠️ Scrollable container not found, will try anyway")
            
            previous_count = 0
            no_change_count = 0
            max_no_change = 8  # Increased attempts
            scroll_attempts = 0
            max_scroll_attempts = 50  # Maximum scroll attempts
            
            while scroll_attempts < max_scroll_attempts:
                scroll_attempts += 1
                
                # Count current reviews
                current_count = await self.page.evaluate("""
                    () => {
                        let reviews = document.querySelectorAll('div[data-review-id]');
                        if (reviews.length === 0) {
                            reviews = document.querySelectorAll('div.jftiEf');
                        }
                        return reviews.length;
                    }
                """)
                
                print(f"  Loaded {current_count} reviews (attempt {scroll_attempts})...", end='\r')
                
                # Check if we have enough reviews
                if max_reviews and current_count >= max_reviews:
                    print(f"\n✓ Reached target of {max_reviews} reviews")
                    break
                
                # Scroll the REVIEWS container specifically (not locations)
                scroll_result = await self.page.evaluate("""
                    () => {
                        // Find the marked reviews feed
                        let feed = document.querySelector('div[data-reviews-feed="true"]');
                        
                        if (!feed) {
                            // Emergency fallback: find ANY scrollable container with reviews
                            const reviews = document.querySelectorAll('div[data-review-id]');
                            if (reviews.length > 0) {
                                // Try to find scrollable parent
                                let parent = reviews[0].parentElement;
                                let attempts = 0;
                                while (parent && attempts < 10) {
                                    if (parent.scrollHeight > parent.clientHeight && parent.clientHeight > 100) {
                                        feed = parent;
                                        console.log('Found scrollable parent at level', attempts);
                                        break;
                                    }
                                    parent = parent.parentElement;
                                    attempts++;
                                }
                            }
                        }
                        
                        if (feed) {
                            const oldScroll = feed.scrollTop;
                            const oldHeight = feed.scrollHeight;
                            const clientHeight = feed.clientHeight;
                            
                            // Scroll down
                            feed.scrollTop = oldScroll + 800;
                            
                            // Force a small wait
                            const startTime = Date.now();
                            while (Date.now() - startTime < 200) {
                                // Busy wait for 200ms
                            }
                            
                            const newScroll = feed.scrollTop;
                            const newHeight = feed.scrollHeight;
                            
                            // Check if at bottom
                            const distanceFromBottom = newHeight - (newScroll + clientHeight);
                            const atBottom = distanceFromBottom < 100 && oldScroll === newScroll;
                            
                            return { 
                                method: 'reviews_feed', 
                                scrolled: newScroll - oldScroll, 
                                at_bottom: atBottom,
                                scroll_pos: newScroll,
                                scroll_height: newHeight,
                                client_height: clientHeight,
                                distance_from_bottom: distanceFromBottom,
                                found: true
                            };
                        }
                        
                        return { method: 'none', at_bottom: false, found: false };
                    }
                """)
                
                if not scroll_result.get('found'):
                    print(f"\n⚠️ Could not find reviews container to scroll")
                    break
                
                # Wait longer for new reviews to load
                await asyncio.sleep(random.uniform(2.5, 3.5))
                
                # Check again after waiting
                new_count = await self.page.evaluate("""
                    () => {
                        let reviews = document.querySelectorAll('div[data-review-id]');
                        if (reviews.length === 0) {
                            reviews = document.querySelectorAll('div.jftiEf');
                        }
                        return reviews.length;
                    }
                """)
                
                # Update count after waiting
                if new_count > current_count:
                    current_count = new_count
                    print(f"  Loaded {current_count} reviews (attempt {scroll_attempts})...", end='\r')
                
                # Only stop if BOTH at_bottom and count didn't change
                if scroll_result.get('at_bottom') and current_count == previous_count:
                    no_change_count += 1
                    if no_change_count >= max_no_change:
                        print(f"\n✓ Reached end of reviews (no more content)")
                        break
                else:
                    # Reset if we're still scrolling or getting new reviews
                    if current_count > previous_count:
                        no_change_count = 0
                
                previous_count = current_count
            
            print(f"\n✓ Finished scrolling. Total reviews visible: {current_count}")
            return current_count
            
        except Exception as e:
            print(f"⚠️ Error scrolling reviews: {e}")
            return 0

    async def _extract_reviews(self, max_reviews: Optional[int] = None) -> List[Dict]:
        """Extract review details from the page."""
        reviews = []
        seen_reviewers = set()  # Track unique reviews to avoid duplicates
        
        try:
            # Try multiple selectors to find review elements
            review_elements = []
            selectors_to_try = [
                'div[data-review-id]',  # Most reliable
                'div.jftiEf',
            ]
            
            for selector in selectors_to_try:
                review_elements = await self.page.query_selector_all(selector)
                if len(review_elements) > 0:
                    print(f"✓ Using selector: {selector}")
                    break
            
            if len(review_elements) == 0:
                print("⚠️ No reviews found with any selector")
                return reviews
            
            total = len(review_elements)
            if max_reviews:
                total = min(total, max_reviews)
            
            print(f"📊 Extracting {total} reviews...")
            
            for idx, review_elem in enumerate(review_elements[:total], 1):
                try:
                    print(f"  Processing {idx}/{total}...", end='\r')
                    
                    review_data = {
                        'reviewer_name': None,
                        'review_date': None,
                        'rating': None,
                        'review_text': None,
                        'pictures': 'no',
                        'company_reply': 'no'
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
                        # Method 1: aria-label
                        rating_elem = await review_elem.query_selector('span[role="img"][aria-label*="star"]')
                        if rating_elem:
                            aria_label = await rating_elem.get_attribute('aria-label')
                            rating_match = re.search(r'(\d+)\s*star', aria_label, re.IGNORECASE)
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
                    
                    # Extract review date - improved method
                    try:
                        # Get all text spans in the review
                        all_spans = await review_elem.query_selector_all('span')
                        found_date = False
                        
                        for span in all_spans:
                            if found_date:
                                break
                                
                            text = await span.inner_text()
                            text = text.strip()
                            
                            # Check if it looks like a date/time
                            date_patterns = [
                                'ago', 'week', 'month', 'day', 'year', 'minute', 'hour',
                                'منذ', 'يوم', 'أيام', 'شهر', 'سنة', 'ساعة', 'قبل',  # Arabic
                                'vor', 'tag', 'woche', 'monat', 'jahr', 'stunde',  # German
                                'edited', 'تعديل', 'تاريخ',  # Edited indicators
                            ]
                            
                            if text and 3 < len(text) < 100:  # Dates are usually short but not too short
                                text_lower = text.lower()
                                if any(pattern in text_lower for pattern in date_patterns):
                                    # Skip if it contains too many words (probably not a date)
                                    word_count = len(text.split())
                                    if word_count <= 6:  # Dates usually have max 5-6 words
                                        review_data['review_date'] = text
                                        found_date = True
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
                    
                    # Check for pictures - try multiple selectors
                    try:
                        image_selectors = [
                            'button[aria-label*="photo"]',
                            'button[jsaction*="photo"]',
                            'img[src*="googleusercontent"]',
                            'button.Tya61d',
                        ]
                        for selector in image_selectors:
                            images = await review_elem.query_selector_all(selector)
                            if images and len(images) > 0:
                                review_data['pictures'] = 'yes'
                                break
                    except:
                        pass
                    
                    # Extract company reply - try multiple selectors
                    try:
                        reply_selectors = [
                            'div[class*="CDe7pd"]',
                            'div[aria-label*="Response from"]',
                            'div.wiI7pd',
                            'div[data-review-id] + div',
                        ]
                        for selector in reply_selectors:
                            reply_elem = await review_elem.query_selector(selector)
                            if reply_elem:
                                reply_text = await reply_elem.inner_text()
                                # Check if it's actually a reply (not empty and not same as review)
                                if reply_text and reply_text.strip() and len(reply_text.strip()) > 5:
                                    # Check for "Response from" or owner indicator
                                    if 'response' in reply_text.lower() or 'owner' in reply_text.lower():
                                        review_data['company_reply'] = reply_text.strip()
                                        break
                    except:
                        pass
                    
                    # Create unique key to check for duplicates
                    review_key = f"{review_data.get('reviewer_name', '')}_{review_data.get('review_text', '')[:50]}"
                    
                    # Only add if not a duplicate
                    if review_key not in seen_reviewers:
                        seen_reviewers.add(review_key)
                        reviews.append(review_data)
                    
                except Exception as e:
                    print(f"\n⚠️ Error extracting review {idx}: {e}")
                    continue
            
            print(f"\n✓ Successfully extracted {len(reviews)} unique reviews (removed {total - len(reviews)} duplicates)")
            return reviews
            
        except Exception as e:
            print(f"❌ Error in review extraction: {e}")
            return reviews

    async def scrape(self, maps_url: str, max_reviews: Optional[int] = None) -> List[Dict]:
        """
        Main scraping function for reviews.
        
        Args:
            maps_url: Google Maps place URL
            max_reviews: Maximum number of reviews to scrape (None = all)
            
        Returns:
            List of review dictionaries
        """
        reviews = []
        
        try:
            # Setup browser
            await self._setup_browser()
            
            # Force English language by adding hl=en parameter to URL
            if '?' in maps_url:
                if 'hl=' not in maps_url:
                    maps_url = maps_url + '&hl=en'
            else:
                maps_url = maps_url + '?hl=en'
            
            # Navigate to URL
            print(f"🌐 Navigating to Google Maps place...")
            await self.page.goto(maps_url, wait_until='domcontentloaded', timeout=60000)
            await asyncio.sleep(4)
            
            # Handle consent first
            await self._handle_consent_dialog()
            await asyncio.sleep(2)
            
            # Get current URL
            current_url = self.page.url
            print(f"📍 Current URL: {current_url}")
            
            # Take initial screenshot
            if not self.headless:
                try:
                    await self.page.screenshot(path='debug_1_initial.png', full_page=True)
                    print("📸 Screenshot: debug_1_initial.png")
                except:
                    pass
            
            # CRITICAL FIX: Use JavaScript to directly click the Reviews tab
            print("🔍 Using JavaScript to find and click Reviews tab...")
            reviews_opened = await self._force_open_reviews_with_js()
            
            # Take screenshot after attempting to open reviews
            if not self.headless:
                try:
                    await self.page.screenshot(path='debug_2_after_reviews_click.png', full_page=True)
                    print("📸 Screenshot: debug_2_after_reviews_click.png")
                except:
                    pass
            
            if not reviews_opened:
                print("⚠️ Could not open reviews tab, trying fallback method...")
                # Fallback: Try the old click method
                reviews_opened = await self._click_reviews_tab()
            
            # Take final screenshot
            if not self.headless:
                try:
                    await self.page.screenshot(path='debug_3_final.png', full_page=True)
                    print("📸 Screenshot: debug_3_final.png")
                except:
                    pass
            
            # Scroll to load more reviews
            await self._scroll_reviews(max_reviews)
            
            # Extract reviews
            reviews = await self._extract_reviews(max_reviews)
            
        except Exception as e:
            print(f"❌ Error during scraping: {e}")
            raise
        
        finally:
            await self.cleanup()
        
        return reviews

    async def cleanup(self):
        """Close browser and cleanup resources."""
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()


async def scrape_google_maps_reviews(maps_url: str, headless: bool = True, max_reviews: Optional[int] = None) -> List[Dict]:
    """
    Convenience function to scrape Google Maps reviews.
    
    Args:
        maps_url: Google Maps place URL
        headless: Run browser in headless mode
        max_reviews: Maximum number of reviews to scrape
        
    Returns:
        List of review dictionaries
    """
    scraper = GoogleMapsReviewsScraper(headless=headless)
    return await scraper.scrape(maps_url, max_reviews)
