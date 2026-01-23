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
                'div[data-review-id]',  # Most reliable
                'div.jftiEf',  # Common review container
                'div[jsaction*="review"]',  # Has review-related actions
                'div.MyEned',  # Review wrapper
                'div.GHT2ce',  # Alternative wrapper
                'div[class*="review"]',  # Contains "review" in class
                'div.fontBodyMedium',  # Body text container (less reliable)
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
            max_no_change = 20  # Increased from 15 to 20 for more patience
            scroll_attempts = 0
            max_scroll_attempts = 150  # Increased from 100 to 150
            
            print("  Using aggressive scrolling strategy...")
            
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
                        return reviews.length;
                    }
                """)
                
                print(f"  Loaded {current_count} reviews... (attempt {scroll_attempts})", end='\r')
                
                # Check if we have enough reviews
                if max_reviews and current_count >= max_reviews:
                    print(f"\n✓ Reached target of {max_reviews} reviews")
                    break
                
                # AGGRESSIVE SCROLLING - Multiple methods
                try:
                    # Method 1: Scroll the feed container
                    await self.page.evaluate("""
                        () => {
                            const feed = document.querySelector('div[role="feed"]');
                            const scrollableDiv = document.querySelector('.m6QErb.DxyBCb.kA9KIf.dS8AEf');
                            const container = feed || scrollableDiv;
                            
                            if (container) {
                                // Scroll down by 800px
                                container.scrollTop += 800;
                            }
                        }
                    """)
                    
                    # Method 2: Press PageDown key (simulates user behavior)
                    await self.page.keyboard.press('PageDown')
                    await asyncio.sleep(0.5)
                    
                    # Method 3: Scroll last review into view
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
                    print(f"\n⚠️ Scroll error: {scroll_error}")
                
                # Wait for content to load (longer wait for better loading)
                await asyncio.sleep(random.uniform(2, 3))
                
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
        
        try:
            # Try multiple selectors to find review elements
            review_elements = []
            selectors_to_try = [
                'div[data-review-id]',
                'div.jftiEf',
                'div[jsaction*="review"]',
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
                    
                    reviews.append(review_data)
                    
                    # Call the callback function if provided (for real-time processing)
                    if on_review_callback:
                        try:
                            print(f"\n📤 Calling webhook callback for review {idx}/{total}")
                            await on_review_callback(review_data, idx, total)
                        except Exception as callback_error:
                            print(f"\n⚠️ Callback error: {callback_error}")
                    
                except Exception as e:
                    print(f"\n⚠️ Error extracting review {idx}: {e}")
                    continue
            
            print(f"\n✓ Successfully extracted {len(reviews)} reviews")
            return reviews
            
        except Exception as e:
            print(f"❌ Error in review extraction: {e}")
            return reviews

    async def scrape(self, maps_url: str, max_reviews: Optional[int] = None, on_review_callback=None) -> List[Dict]:
        """
        Main scraping function for reviews.
        
        Args:
            maps_url: Google Maps place URL
            max_reviews: Maximum number of reviews to scrape (None = all)
            on_review_callback: Optional async callback function called after each review is extracted
            
        Returns:
            List of review dictionaries
        """
        reviews = []
        
        try:
            # Setup browser
            await self._setup_browser()
            
            # Navigate to URL
            print(f"🌐 Navigating to Google Maps place...")
            await self.page.goto(maps_url, wait_until='domcontentloaded', timeout=60000)
            await asyncio.sleep(4)
            
            # Take screenshot for debugging
            if not self.headless:
                try:
                    await self.page.screenshot(path='debug_1_initial.png', full_page=True)
                    print("📸 Screenshot saved: debug_1_initial.png")
                except:
                    pass
            
            # Handle consent
            await self._handle_consent_dialog()
            await asyncio.sleep(2)
            
            # Take screenshot after consent
            if not self.headless:
                try:
                    await self.page.screenshot(path='debug_2_after_consent.png', full_page=True)
                    print("📸 Screenshot saved: debug_2_after_consent.png")
                except:
                    pass
            
            # Click on reviews tab
            reviews_opened = await self._click_reviews_tab()
            
            # Take screenshot after clicking reviews
            if not self.headless:
                try:
                    await self.page.screenshot(path='debug_3_after_reviews_click.png', full_page=True)
                    print("📸 Screenshot saved: debug_3_after_reviews_click.png")
                except:
                    pass
            
            if not reviews_opened:
                print("⚠️ Reviews tab not found, trying to extract from current view...")
            # Temporarily disabled: sorting causes issues with current Google Maps layout
            # else:
            #     # Sort by lowest rating
            #     await self._sort_by_lowest_rating()
            
            # Scroll to load more reviews
            await self._scroll_reviews(max_reviews)
            
            # Extract reviews with callback
            reviews = await self._extract_reviews(max_reviews, on_review_callback)
            
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


async def scrape_google_maps_reviews(maps_url: str, headless: bool = True, max_reviews: Optional[int] = None, on_review_callback=None) -> List[Dict]:
    """
    Convenience function to scrape Google Maps reviews.
    
    Args:
        maps_url: Google Maps place URL
        headless: Run browser in headless mode
        max_reviews: Maximum number of reviews to scrape
        on_review_callback: Optional async callback function called after each review
        
    Returns:
        List of review dictionaries
    """
    scraper = GoogleMapsReviewsScraper(headless=headless)
    return await scraper.scrape(maps_url, max_reviews, on_review_callback)
