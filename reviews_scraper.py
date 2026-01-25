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
            
            # Try to find and click reviews tab - with more selectors
            reviews_selectors = [
                'button[aria-label*="Reviews"]',
                'button[aria-label*="reviews"]',
                'button[data-tab-index="1"]',  # Usually reviews is the 2nd tab (0-indexed)
                'button:has-text("Reviews")',
                'button:has-text("reviews")',
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
                        
                        allDivs.forEach(div => {
                            // Check if this div has a star rating indicator
                            const hasStars = div.querySelector('span[role="img"][aria-label*="star"]') ||
                                           div.querySelector('span[aria-label*="stars"]') ||
                                           div.querySelector('[aria-label*="Star rating"]');
                            
                            // Check if it has date-like text
                            const text = div.innerText || '';
                            const hasDate = text.includes('ago') || text.includes('week') || 
                                          text.includes('month') || text.includes('day') ||
                                          text.includes('year');
                            
                            // Check if it has substantial text (likely review content)
                            const hasContent = text.length > 100;
                            
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
                            
                            // Strategy 3: Find by checking parent structure (reviews are usually in right panel)
                            if (!reviewsFeed) {
                                const allScrollable = document.querySelectorAll('div[style*="overflow"]');
                                for (let div of allScrollable) {
                                    const hasReviews = div.querySelector('div[data-review-id]') || 
                                                      div.querySelector('div.jftiEf');
                                    const rect = div.getBoundingClientRect();
                                    // Check if it's on the right side of screen (reviews panel)
                                    if (hasReviews && rect.left > window.innerWidth / 3) {
                                        reviewsFeed = div;
                                        method = 'right_panel';
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
                
                # Track progress
                if current_count == previous_count:
                    no_change_count += 1
                    
                    # If stuck for 5 attempts, try extra aggressive scroll
                    if no_change_count == 5:
                        print(f"\n🔄 Stuck at {current_count} reviews, trying extra aggressive scroll...")
                        for _ in range(3):
                            await self.page.keyboard.press('End')
                            await asyncio.sleep(1)
                            await self.page.keyboard.press('PageDown')
                            await asyncio.sleep(1)
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
                    
                    # Extract review date - try multiple selectors
                    try:
                        date_selectors = [
                            'span[class*="rsqaWe"]',
                            'span.DU9Pgb',
                            'span[aria-label]',
                        ]
                        for selector in date_selectors:
                            date_elem = await review_elem.query_selector(selector)
                            if date_elem:
                                text = await date_elem.inner_text()
                                # Check if it looks like a date
                                if any(word in text.lower() for word in ['ago', 'week', 'month', 'day', 'year']):
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
                    
                    # Check for pictures - try multiple selectors
                    try:
                        image_selectors = [
                            'button[aria-label*="photo"]',
                            'button[aria-label*="Photo"]',
                            'button[jsaction*="photo"]',
                            'img[src*="googleusercontent"]',
                            'img[src*="ggpht"]',
                            'button.Tya61d',
                            'button[data-photo-index]',
                        ]
                        has_images = False
                        for selector in image_selectors:
                            images = await review_elem.query_selector_all(selector)
                            if images and len(images) > 0:
                                # Additional check: make sure it's not a profile picture
                                for img in images:
                                    try:
                                        aria_label = await img.get_attribute('aria-label')
                                        # Skip if it's a profile picture
                                        if aria_label and ('profile' in aria_label.lower() or 'avatar' in aria_label.lower()):
                                            continue
                                        has_images = True
                                        break
                                    except:
                                        has_images = True
                                        break
                            if has_images:
                                break
                        
                        if has_images:
                            review_data['pictures'] = 'yes'
                        else:
                            review_data['pictures'] = 'no'
                    except:
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
            reviews = await self._extract_reviews(max_reviews, on_review_callback)
            
        except Exception as e:
            print(f"❌ Error during scraping: {e}")
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
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()


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
