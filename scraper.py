import asyncio
import random
import re
from typing import List, Dict, Optional
from playwright.async_api import async_playwright, Page, Browser, BrowserContext


class GoogleMapsScraper:
    """
    Production-grade Google Maps scraper with anti-detection mechanisms.
    """

    def __init__(self, headless: bool = True):
        self.headless = headless
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None

    async def _setup_browser(self):
        """Initialize browser with stealth configurations."""
        playwright = await async_playwright().start()
        
        # Launch Chromium with server-friendly arguments
        self.browser = await playwright.chromium.launch(
            headless=self.headless,
            args=[
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-blink-features=AutomationControlled',
                '--disable-web-security',
            ]
        )

        # Create context with realistic settings
        self.context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            locale='en-US',
            timezone_id='America/New_York',
        )

        # Add extra HTTP headers
        await self.context.set_extra_http_headers({
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        })

        self.page = await self.context.new_page()

        # Apply comprehensive stealth JavaScript
        await self.page.add_init_script("""
            // Remove webdriver property
            Object.defineProperty(navigator, 'webdriver', {
                get: () => false,
            });
            
            // Override the permission query
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
            
            // Mock plugins
            Object.defineProperty(navigator, 'plugins', {
                get: () => {
                    const plugin = {
                        0: { type: "application/x-google-chrome-pdf", suffixes: "pdf", description: "Portable Document Format" },
                        description: "Portable Document Format",
                        filename: "internal-pdf-viewer",
                        length: 1,
                        name: "Chrome PDF Plugin"
                    };
                    return [plugin, plugin, plugin];
                },
            });
            
            // Mock languages
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en'],
            });
            
            // Mock chrome property
            if (!window.chrome) {
                window.chrome = {};
            }
            window.chrome.runtime = {
                connect: function() {},
                sendMessage: function() {},
            };
            
            // Mock permissions
            const originalPermissions = navigator.permissions;
            Object.defineProperty(navigator, 'permissions', {
                get: () => ({
                    query: (parameters) => (
                        parameters.name === 'notifications' ?
                            Promise.resolve({ state: 'prompt' }) :
                            originalPermissions.query(parameters)
                    )
                }),
            });
            
            // Mock vendor
            Object.defineProperty(navigator, 'vendor', {
                get: () => 'Google Inc.',
            });
            
            // Mock platform
            Object.defineProperty(navigator, 'platform', {
                get: () => 'MacIntel',
            });
            
            // Mock connection
            Object.defineProperty(navigator, 'connection', {
                get: () => ({
                    effectiveType: '4g',
                    rtt: 100,
                    downlink: 10,
                    saveData: false,
                }),
            });
        """)

    async def _handle_consent_dialog(self):
        """Handle Google's cookie consent dialog if it appears."""
        try:
            # Wait for consent button with multiple possible selectors
            consent_selectors = [
                'button:has-text("Accept all")',
                'button:has-text("I agree")',
                'button:has-text("Agree")',
                'button[aria-label*="Accept"]',
                'button:has-text("Reject all")',  # Fallback
            ]

            for selector in consent_selectors:
                try:
                    consent_button = await self.page.wait_for_selector(
                        selector, timeout=3000
                    )
                    if consent_button:
                        await consent_button.click()
                        await asyncio.sleep(random.uniform(1, 2))
                        print("✓ Handled consent dialog")
                        return
                except:
                    continue

        except Exception as e:
            print(f"No consent dialog found or already accepted: {e}")

    async def _search_location(self, search_term: str):
        """Navigate to Google Maps and perform the search."""
        # Go to Google Maps with English language
        print(f"🌐 Navigating to Google Maps...")
        await self.page.goto('https://www.google.com/maps?hl=en', wait_until='domcontentloaded')
        
        await asyncio.sleep(random.uniform(2, 3))

        # Handle consent if needed
        await self._handle_consent_dialog()

        # Find search box and type query
        print(f"🔍 Searching for: {search_term}")
        
        # Try multiple selectors for the search box
        search_selectors = [
            'input#searchboxinput',
            'input[aria-label*="Search"]',
            'input[placeholder*="Search"]',
            'input[name="q"]',
            'input.searchboxinput',
        ]
        
        search_box = None
        for selector in search_selectors:
            try:
                search_box = await self.page.wait_for_selector(selector, timeout=3000)
                if search_box:
                    print(f"✓ Found search box using selector: {selector}")
                    break
            except:
                continue
        
        if not search_box:
            raise Exception("Could not find search box on Google Maps")
        
        await search_box.click()
        await asyncio.sleep(random.uniform(0.5, 1))
        
        # Clear any existing text
        await search_box.fill('')
        await asyncio.sleep(random.uniform(0.3, 0.5))
        
        # Type with human-like delays
        await search_box.type(search_term, delay=random.randint(50, 150))
        await asyncio.sleep(random.uniform(0.5, 1))
        
        # Press Enter
        await self.page.keyboard.press('Enter')
        
        # Wait for results to load
        print("⏳ Waiting for results to load...")
        await self.page.wait_for_selector('div[role="feed"]', timeout=15000)
        await asyncio.sleep(random.uniform(2, 3))

    async def _scroll_feed(self):
        """Scroll through the results feed to load all listings."""
        print("📜 Scrolling through results...")
        
        # Find the scrollable feed container
        feed_selector = 'div[role="feed"]'
        
        previous_height = 0
        no_change_count = 0
        max_no_change = 3  # Stop after 3 consecutive no-change scrolls
        
        while no_change_count < max_no_change:
            # Get current scroll height
            current_height = await self.page.evaluate(f"""
                () => {{
                    const feed = document.querySelector('{feed_selector}');
                    return feed ? feed.scrollHeight : 0;
                }}
            """)
            
            # Scroll down
            await self.page.evaluate(f"""
                () => {{
                    const feed = document.querySelector('{feed_selector}');
                    if (feed) {{
                        feed.scrollTo(0, feed.scrollHeight);
                    }}
                }}
            """)
            
            # Random human-like delay
            await asyncio.sleep(random.uniform(1.5, 3))
            
            # Check if we've reached the bottom
            if current_height == previous_height:
                no_change_count += 1
            else:
                no_change_count = 0
            
            previous_height = current_height
            
        print(f"✓ Scrolling complete. Loaded all available results.")

    async def _extract_contact_from_website(self, website_url: str) -> Dict[str, Optional[str]]:
        """Visit a website and extract email address and phone number."""
        result = {'email': None, 'phone': None}
        
        if not website_url:
            return result
            
        try:
            # Create a new page for visiting the website
            website_page = await self.context.new_page()
            
            # Set timeout and visit the website
            await website_page.goto(website_url, timeout=10000, wait_until='domcontentloaded')
            await asyncio.sleep(random.uniform(1, 2))
            
            # Get page content
            page_content = await website_page.content()
            page_text = await website_page.inner_text('body')
            
            # Extract EMAIL
            # Common email regex patterns
            email_patterns = [
                r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            ]
            
            # Look for emails in the content
            for pattern in email_patterns:
                matches = re.findall(pattern, page_content, re.IGNORECASE)
                if matches:
                    # Filter out common false positives
                    valid_emails = [
                        email for email in matches 
                        if not any(skip in email.lower() for skip in [
                            'example.com', 'test.com', 'domain.com', 
                            'youremail', 'email@', 'wix.com', 'sentry.io',
                            'schema.org', 'w3.org', 'placeholder', 'yoursite.com'
                        ])
                    ]
                    if valid_emails:
                        result['email'] = valid_emails[0]
                        break
            
            # If no email found, try to find email links (mailto:)
            if not result['email']:
                mailto_elements = await website_page.query_selector_all('a[href^="mailto:"]')
                if mailto_elements:
                    href = await mailto_elements[0].get_attribute('href')
                    email = href.replace('mailto:', '').split('?')[0]
                    result['email'] = email
            
            # Extract PHONE NUMBER
            # Phone number patterns (international and local formats)
            phone_patterns = [
                r'\+?\d{1,4}[\s\-]?\(?\d{1,4}\)?[\s\-]?\d{1,4}[\s\-]?\d{1,4}[\s\-]?\d{1,9}',  # International
                r'\(\d{3}\)\s*\d{3}[-\s]?\d{4}',  # (123) 456-7890
                r'\d{3}[-\.\s]\d{3}[-\.\s]\d{4}',  # 123-456-7890
                r'\d{10,}',  # 10+ digits
            ]
            
            # Try to find phone in tel: links first (most reliable)
            tel_elements = await website_page.query_selector_all('a[href^="tel:"]')
            if tel_elements:
                href = await tel_elements[0].get_attribute('href')
                phone = href.replace('tel:', '').strip()
                # Clean up the phone number
                phone = re.sub(r'[^\d\+\-\(\)\s]', '', phone)
                if len(phone) >= 10:
                    result['phone'] = phone
            
            # If no phone found in tel: links, search in page text
            if not result['phone']:
                for pattern in phone_patterns:
                    matches = re.findall(pattern, page_text)
                    if matches:
                        # Filter and validate phone numbers
                        for match in matches:
                            # Remove spaces and dashes for validation
                            cleaned = re.sub(r'[\s\-\(\)\.]', '', match)
                            # Check if it's a valid phone number (10-15 digits)
                            if cleaned.isdigit() and 10 <= len(cleaned) <= 15:
                                result['phone'] = match.strip()
                                break
                        if result['phone']:
                            break
            
            await website_page.close()
            
        except Exception as e:
            print(f"    ⚠️ Could not extract contact info from website: {e}")
            try:
                await website_page.close()
            except:
                pass
            
        return result

    async def _extract_review_breakdown(self) -> Dict:
        """Extract star rating breakdown (5-star, 4-star, etc.)."""
        breakdown = {
            'one_star': None,
            'two_star': None,
            'three_star': None,
            'four_star': None,
            'five_star': None,
        }
        
        try:
            # Try to find and click the reviews button
            reviews_button_selectors = [
                'button[jsaction*="pane.rating"]',
                'button[aria-label*="reviews"]',
                'button[aria-label*="Reviews"]',
                'div.F7nice button',
                'button[data-tab-index="1"]',
            ]
            
            clicked = False
            for selector in reviews_button_selectors:
                try:
                    reviews_button = await self.page.query_selector(selector)
                    if reviews_button:
                        # Scroll to button if needed
                        try:
                            await reviews_button.scroll_into_view_if_needed()
                            await asyncio.sleep(0.5)
                        except:
                            pass
                        
                        # Try JavaScript click first (more reliable)
                        try:
                            await self.page.evaluate('(button) => button.click()', reviews_button)
                            clicked = True
                            print(f"      → Clicked reviews button (JS)")
                        except:
                            # Fallback to regular click
                            try:
                                await reviews_button.click(timeout=3000)
                                clicked = True
                                print(f"      → Clicked reviews button")
                            except:
                                pass
                        
                        if clicked:
                            await asyncio.sleep(random.uniform(3, 4))
                            break
                except Exception as e:
                    continue
            
            if not clicked:
                print(f"      → Could not click reviews button, trying direct extraction...")
                # Try to extract from current page without clicking
                try:
                    star_data = await self.page.evaluate("""
                        () => {
                            const data = {};
                            const allText = document.body.innerText;
                            const lines = allText.split('\\n').map(l => l.trim());
                            
                            for (let i = 0; i < lines.length; i++) {
                                const line = lines[i];
                                if (/^[1-5]$/.test(line)) {
                                    const starNum = parseInt(line);
                                    for (let j = i; j < Math.min(i + 3, lines.length); j++) {
                                        const countMatch = lines[j].match(/^([\\d,]+)$/);
                                        if (countMatch) {
                                            const count = parseInt(countMatch[1].replace(/,/g, ''));
                                            if (count > 0 && !data[starNum]) {
                                                data[starNum] = count;
                                                break;
                                            }
                                        }
                                    }
                                }
                            }
                            return data;
                        }
                    """)
                    
                    if star_data:
                        breakdown['five_star'] = star_data.get('5') or star_data.get(5)
                        breakdown['four_star'] = star_data.get('4') or star_data.get(4)
                        breakdown['three_star'] = star_data.get('3') or star_data.get(3)
                        breakdown['two_star'] = star_data.get('2') or star_data.get(2)
                        breakdown['one_star'] = star_data.get('1') or star_data.get(1)
                except:
                    pass
                
                return breakdown
            
            # Wait for reviews panel to fully load
            await asyncio.sleep(2)
            
            # Enhanced JavaScript extraction with multiple methods
            star_data = await self.page.evaluate("""
                () => {
                    const data = {};
                    
                    // Method 1: Look for table rows with aria-label
                    const rows = document.querySelectorAll('tr[aria-label]');
                    rows.forEach(row => {
                        const label = row.getAttribute('aria-label');
                        if (label) {
                            // Match "5 stars, 123 reviews" or similar patterns
                            const match = label.match(/(\\d)\\s+(?:star|stars).*?(\\d+)\\s+(?:review|reviews)/i);
                            if (match) {
                                const stars = parseInt(match[1]);
                                const count = parseInt(match[2]);
                                if (stars >= 1 && stars <= 5) {
                                    data[stars] = count;
                                }
                            }
                        }
                    });
                    
                    // Method 2: Look for specific histogram structure
                    if (Object.keys(data).length === 0) {
                        const histogramRows = document.querySelectorAll('tr');
                        histogramRows.forEach(row => {
                            const cells = row.querySelectorAll('td');
                            if (cells.length >= 2) {
                                const firstCell = cells[0].innerText.trim();
                                const lastCell = cells[cells.length - 1].innerText.trim();
                                
                                // Try to extract star number from first cell
                                const starMatch = firstCell.match(/^(\\d)$/);
                                const countMatch = lastCell.match(/^([\\d,]+)$/);
                                
                                if (starMatch && countMatch) {
                                    const stars = parseInt(starMatch[1]);
                                    const count = parseInt(countMatch[1].replace(/,/g, ''));
                                    if (stars >= 1 && stars <= 5 && count > 0) {
                                        data[stars] = count;
                                    }
                                }
                            }
                        });
                    }
                    
                    // Method 3: Look for buttons with aria-label containing star info
                    if (Object.keys(data).length === 0) {
                        const buttons = document.querySelectorAll('button[aria-label]');
                        buttons.forEach(btn => {
                            const label = btn.getAttribute('aria-label');
                            if (label && label.match(/\\d\\s+stars?/i)) {
                                const match = label.match(/(\\d)\\s+(?:star|stars),\\s*([\\d,]+)\\s+(?:review|reviews)/i);
                                if (match) {
                                    const stars = parseInt(match[1]);
                                    const count = parseInt(match[2].replace(/,/g, ''));
                                    if (stars >= 1 && stars <= 5) {
                                        data[stars] = count;
                                    }
                                }
                            }
                        });
                    }
                    
                    // Method 4: Text-based extraction from page
                    if (Object.keys(data).length === 0) {
                        const allText = document.body.innerText;
                        const lines = allText.split('\\n').map(l => l.trim());
                        
                        for (let i = 0; i < lines.length; i++) {
                            const line = lines[i];
                            
                            // Look for standalone number (1-5) followed by a count on same or next line
                            if (/^[1-5]$/.test(line)) {
                                const starNum = parseInt(line);
                                
                                // Check same line or next few lines for count
                                for (let j = i; j < Math.min(i + 3, lines.length); j++) {
                                    const countMatch = lines[j].match(/^([\\d,]+)$/);
                                    if (countMatch) {
                                        const count = parseInt(countMatch[1].replace(/,/g, ''));
                                        if (count > 0 && !data[starNum]) {
                                            data[starNum] = count;
                                            break;
                                        }
                                    }
                                }
                            }
                        }
                    }
                    
                    return data;
                }
            """)
            
            if star_data and isinstance(star_data, dict):
                breakdown['five_star'] = star_data.get('5') or star_data.get(5)
                breakdown['four_star'] = star_data.get('4') or star_data.get(4)
                breakdown['three_star'] = star_data.get('3') or star_data.get(3)
                breakdown['two_star'] = star_data.get('2') or star_data.get(2)
                breakdown['one_star'] = star_data.get('1') or star_data.get(1)
                
                found_count = sum(1 for v in breakdown.values() if v is not None)
                print(f"      → Extracted {found_count}/5 star categories")
            else:
                print(f"      → No star breakdown data found")
            
            # Go back to main view
            try:
                await self.page.keyboard.press('Escape')
                await asyncio.sleep(0.5)
            except:
                pass
                
        except Exception as e:
            print(f"      → Error in breakdown extraction: {e}")
        
        return breakdown

    async def _extract_place_details(self, article) -> Dict:
        """Extract details from a single place card."""
        details = {
            'business_name': None,
            'rating': None,
            'review_count': None,
            'phone': None,
            'website': None,
            'address': None,
            'email': None,
            'one_star': None,
            'two_star': None,
            'three_star': None,
            'four_star': None,
            'five_star': None,
        }

        try:
            # Extract business name
            name_element = await article.query_selector('a[aria-label]')
            if name_element:
                aria_label = await name_element.get_attribute('aria-label')
                details['business_name'] = aria_label

            # Extract rating and review count from the same element
            rating_element = await article.query_selector('span[role="img"][aria-label*="stars"]')
            if rating_element:
                aria_label = await rating_element.get_attribute('aria-label')
                # Parse "4.5 stars" format
                rating_match = re.search(r'([\d.]+)\s*stars?', aria_label, re.IGNORECASE)
                if rating_match:
                    details['rating'] = float(rating_match.group(1))
                
                # Sometimes review count is in the same aria-label: "4.5 stars 123 reviews"
                review_in_label = re.search(r'([\d,]+)\s*reviews?', aria_label, re.IGNORECASE)
                if review_in_label:
                    details['review_count'] = int(review_in_label.group(1).replace(',', ''))

            # Extract review count - try multiple methods
            # Method 1: From aria-label
            review_element = await article.query_selector('span[aria-label*="reviews"]')
            if review_element:
                aria_label = await review_element.get_attribute('aria-label')
                # Parse "123 reviews" format
                review_match = re.search(r'([\d,]+)\s*reviews?', aria_label)
                if review_match:
                    details['review_count'] = int(review_match.group(1).replace(',', ''))
            
            # Method 2: If not found, try getting from article text
            if not details['review_count']:
                try:
                    article_text = await article.inner_text()
                    # Look for patterns like "(123)" or "123 reviews"
                    review_patterns = [
                        r'\(?([\d,]+)\)?\s*reviews?',
                        r'reviews?\s*\(?([\d,]+)\)?',
                    ]
                    for pattern in review_patterns:
                        review_match = re.search(pattern, article_text, re.IGNORECASE)
                        if review_match:
                            details['review_count'] = int(review_match.group(1).replace(',', ''))
                            break
                except:
                    pass

            # Click on the card to load more details
            await article.click()
            await asyncio.sleep(random.uniform(1.5, 2.5))
            
            # CRITICAL FIX: Wait for the detail panel to update with the correct business
            # This prevents extracting data from the wrong business
            if details['business_name']:
                try:
                    # Wait for the panel to show the correct business name
                    # Try multiple times with increasing delays
                    max_attempts = 5
                    panel_updated = False
                    
                    for attempt in range(max_attempts):
                        # Get the current business name shown in the detail panel
                        panel_name = await self.page.evaluate('''() => {
                            // Try multiple selectors for the business name in detail panel
                            const selectors = [
                                'h1[class*="fontHeadline"]',
                                'h1.DUwDvf',
                                'h1',
                                '[role="main"] h1',
                                '.DUwDvf.lfPIob'
                            ];
                            
                            for (const selector of selectors) {
                                const element = document.querySelector(selector);
                                if (element && element.innerText && element.innerText.trim()) {
                                    return element.innerText.trim();
                                }
                            }
                            return null;
                        }''')
                        
                        # Check if panel name matches the expected business name
                        if panel_name and panel_name.strip() == details['business_name'].strip():
                            panel_updated = True
                            print(f"    ✓ Panel updated correctly for: {details['business_name']}")
                            break
                        else:
                            # Panel not updated yet, wait a bit more
                            await asyncio.sleep(0.5)
                    
                    if not panel_updated:
                        print(f"    ⚠️ Warning: Panel may not have updated correctly for {details['business_name']}")
                        # Add extra delay as fallback
                        await asyncio.sleep(1)
                        
                except Exception as e:
                    print(f"    ⚠️ Could not verify panel update: {e}")
                    # Add extra delay as fallback
                    await asyncio.sleep(1)
            
            # Try to extract review count from detail page if still not found
            if not details['review_count']:
                try:
                    detail_text = await self.page.evaluate('() => document.body.innerText')
                    review_match = re.search(r'(\d{1,6})\s*reviews?', detail_text, re.IGNORECASE)
                    if review_match:
                        details['review_count'] = int(review_match.group(1).replace(',', ''))
                except:
                    pass

            # VERIFICATION: Double-check we're on the correct business before extracting contact details
            # This is a final safety check to prevent data mismatch
            try:
                current_panel_name = await self.page.evaluate('''() => {
                    const selectors = ['h1[class*="fontHeadline"]', 'h1.DUwDvf', 'h1'];
                    for (const selector of selectors) {
                        const element = document.querySelector(selector);
                        if (element && element.innerText) {
                            return element.innerText.trim();
                        }
                    }
                    return null;
                }''')
                
                if current_panel_name and details['business_name']:
                    if current_panel_name.strip() != details['business_name'].strip():
                        print(f"    ⚠️ WARNING: Panel name mismatch! Expected '{details['business_name']}' but got '{current_panel_name}'")
                        print(f"    ⚠️ Skipping contact details extraction to avoid data mismatch")
                        # Return early to avoid extracting wrong data
                        return details
            except Exception as e:
                print(f"    ⚠️ Could not verify panel name: {e}")

            # Scroll the detail panel to ensure all contact info is loaded
            try:
                await self.page.evaluate('''() => {
                    const panel = document.querySelector('[role="main"]') || 
                                  document.querySelector('.m6QErb.DxyBCb.kA9KIf.dS8AEf') ||
                                  document.querySelector('div[class*="scrollable"]');
                    if (panel) {
                        panel.scrollTo(0, panel.scrollHeight / 2);
                    }
                }''')
                await asyncio.sleep(0.5)
            except:
                pass

            # Extract website FIRST (we need it to prioritize website data)
            website_element = await self.page.query_selector('a[data-tooltip="Open website"]')
            if website_element:
                website_url = await website_element.get_attribute('href')
                details['website'] = website_url

            # PRIORITY 1: If website exists, try to get email and phone from website FIRST
            if details['website']:
                print(f"    🌐 Visiting website to extract contact info...")
                website_contact = await self._extract_contact_from_website(details['website'])
                
                if website_contact['email']:
                    details['email'] = website_contact['email']
                    print(f"    ✅ Email found on website: {website_contact['email']}")
                
                if website_contact['phone']:
                    details['phone'] = website_contact['phone']
                    print(f"    ✅ Phone found on website: {website_contact['phone']}")

            # PRIORITY 2: If email not found on website, try Google Maps page
            if not details['email']:
                page_content = await self.page.content()
                email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
                email_matches = re.findall(email_pattern, page_content)
                
                if email_matches:
                    # Filter out common false positives
                    valid_emails = [
                        email for email in email_matches 
                        if not any(skip in email.lower() for skip in [
                            'example.com', 'test.com', 'domain.com', 
                            'youremail', 'email@', 'google.com', 'gstatic.com',
                            'schema.org', 'w3.org'
                        ])
                    ]
                    if valid_emails:
                        details['email'] = valid_emails[0]
                        print(f"    ✅ Email found on Google Maps: {valid_emails[0]}")

            # PRIORITY 3: If phone not found on website, try Google Maps
            if not details['phone']:
                phone_selectors = [
                    'button[data-tooltip="Copy phone number"]',
                    'button[aria-label*="Phone"]',
                    'a[href^="tel:"]',
                ]
                
                for selector in phone_selectors:
                    phone_element = await self.page.query_selector(selector)
                    if phone_element:
                        phone_text = await phone_element.inner_text()
                        if phone_text and phone_text.strip():
                            details['phone'] = phone_text.strip()
                            print(f"    ✅ Phone found on Google Maps: {phone_text.strip()}")
                            break

            # Extract address
            address_selectors = [
                'button[data-tooltip="Copy address"]',
                'button[aria-label*="Address"]',
            ]
            
            for selector in address_selectors:
                address_element = await self.page.query_selector(selector)
                if address_element:
                    address_text = await address_element.inner_text()
                    if address_text and address_text.strip():
                        details['address'] = address_text.strip()
                        break
            
            # Extract review breakdown (star distribution) if reviews exist
            if details['review_count'] and details['review_count'] > 0:
                print(f"\n    ⭐ Extracting star breakdown ({details['review_count']} reviews)...")
                breakdown = await self._extract_review_breakdown()
                details['one_star'] = breakdown['one_star']
                details['two_star'] = breakdown['two_star']
                details['three_star'] = breakdown['three_star']
                details['four_star'] = breakdown['four_star']
                details['five_star'] = breakdown['five_star']
                
                # Show what was found with details
                stars_found = [k for k in ['five_star', 'four_star', 'three_star', 'two_star', 'one_star'] 
                              if details.get(k) is not None]
                if stars_found:
                    stars_summary = ', '.join([f"{k.replace('_star', '⭐')}: {details[k]}" for k in stars_found])
                    print(f"    ✓ Star breakdown: {stars_summary}")
                else:
                    print(f"    ✗ Could not extract star breakdown")

        except Exception as e:
            print(f"⚠️ Error extracting details: {e}")

        return details

    async def scrape(self, search_term: str, max_results: Optional[int] = None, on_result_callback=None) -> List[Dict]:
        """
        Main scraping function.
        
        Args:
            search_term: The search query (e.g., "Real Estate Agencies in Cairo")
            max_results: Maximum number of results to extract (None = all available)
            on_result_callback: Optional async callback function called after each result is extracted.
                               Receives the result dict as parameter.
            
        Returns:
            List of dictionaries containing business information
        """
        results = []

        try:
            # Setup browser
            await self._setup_browser()

            # Navigate and search
            await self._search_location(search_term)

            # Scroll to load all results
            await self._scroll_feed()

            # Extract all article cards
            print("📊 Extracting business information...")
            articles = await self.page.query_selector_all('div[role="feed"] > div > div[role="article"]')
            
            # Limit articles if max_results is specified
            if max_results and len(articles) > max_results:
                articles = articles[:max_results]
                print(f"Found {len(articles)} businesses (limited to {max_results}). Extracting details...")
            else:
                print(f"Found {len(articles)} businesses. Extracting details...")

            for idx, article in enumerate(articles, 1):
                print(f"  Processing {idx}/{len(articles)}...", end='\r')
                
                details = await self._extract_place_details(article)
                
                if details['business_name']:
                    results.append(details)
                    
                    # Call the callback function if provided (for real-time processing)
                    if on_result_callback:
                        try:
                            print(f"\n📤 Calling webhook callback for result {idx}/{len(articles)}: {details['business_name']}")
                            await on_result_callback(details, idx, len(articles))
                        except Exception as callback_error:
                            print(f"\n⚠️ Callback error: {callback_error}")
                
                # Random delay between extractions
                await asyncio.sleep(random.uniform(0.5, 1.5))
                
                # Stop if we've reached max_results
                if max_results and len(results) >= max_results:
                    break

            print(f"\n✓ Successfully extracted {len(results)} businesses")

        except Exception as e:
            print(f"❌ Error during scraping: {e}")
            
            # Take screenshot for debugging
            if self.page:
                screenshot_path = f"error_screenshot_{int(asyncio.get_event_loop().time())}.png"
                await self.page.screenshot(path=screenshot_path, full_page=True)
                print(f"📸 Screenshot saved to: {screenshot_path}")
            
            raise

        finally:
            # Cleanup
            await self.cleanup()

        return results

    async def cleanup(self):
        """Close browser and cleanup resources."""
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()


async def scrape_google_maps(search_term: str, headless: bool = True, max_results: Optional[int] = None, on_result_callback=None) -> List[Dict]:
    """
    Convenience function to scrape Google Maps.
    
    Args:
        search_term: Search query
        headless: Run browser in headless mode
        max_results: Maximum number of results to extract (None = all available)
        on_result_callback: Optional async callback function called after each result
        
    Returns:
        List of business information dictionaries
    """
    scraper = GoogleMapsScraper(headless=headless)
    return await scraper.scrape(search_term, max_results=max_results, on_result_callback=on_result_callback)
