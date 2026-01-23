"""
Safari Portal Itinerary Scraper

Uses Playwright to scrape itinerary data from Safari Portal pages,
sends to Claude API for structured JSON transformation,
and saves to MongoDB Atlas.
"""

from datetime import datetime, timedelta
from typing import Optional

from playwright.async_api import async_playwright, Page, Browser
from ..llm_tracker import LLMPerformanceTracker


class ItineraryScraper:
    """Scrapes Safari Portal itineraries and transforms them using multiple LLM providers."""

    def __init__(self, mongo_client=None):
        """
        Initialize the scraper with multiple LLM providers.

        Args:
            mongo_client: PyMongo client instance (optional, for standalone use)
        """
        self.mongo_client = mongo_client
        self.llm_tracker = LLMPerformanceTracker(mongo_client)

        # Load airports data for LLM context
        self.airports_data = self._load_airports()
        print(f"✓ Loaded {len(self.airports_data)} airports for reference")

        # Initialize all available API clients
        self.api_clients = {}

        # Try to initialize Gemini
        try:
            from google import genai
            gemini_key = os.getenv("GEMINI_API_KEY")
            if gemini_key:
                self.api_clients['gemini'] = genai.Client(api_key=gemini_key)
                print("✓ Gemini API initialized")
        except Exception as e:
            print(f"⚠ Gemini API not available: {e}")

        # Try to initialize Claude
        try:
            import anthropic
            claude_key = os.getenv("ANTHROPIC_API_KEY")
            if claude_key:
                self.api_clients['anthropic'] = anthropic.Anthropic(api_key=claude_key)
                print("✓ Claude API initialized")
        except Exception as e:
            print(f"⚠ Claude API not available: {e}")

        # Try to initialize OpenRouter (for Llama, DeepSeek, Qwen, etc.)
        try:
            openrouter_key = os.getenv("OPENROUTER_API_KEY")
            if openrouter_key:
                self.api_clients['openrouter'] = openrouter_key
                print("✓ OpenRouter API initialized")
        except Exception as e:
            print(f"⚠ OpenRouter API not available: {e}")

        # Try to initialize Hugging Face (for open models)
        try:
            hf_key = os.getenv("HUGGINGFACE_API_KEY")
            if hf_key:
                self.api_clients['huggingface'] = hf_key
                print("✓ Hugging Face API initialized")
        except Exception as e:
            print(f"⚠ Hugging Face API not available: {e}")





    def _load_airports(self) -> list:
        """Load airports data from JSON file."""
        try:
            import json
            airports_path = os.path.join(os.path.dirname(__file__), 'airports.json')
            with open(airports_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠ Error loading airports.json: {e}")
            return []

    def _get_relevant_airports(self, countries: list) -> str:
        """
        Get airports relevant to the itinerary countries.

        Args:
            countries: List of country names mentioned in the itinerary

        Returns:
            Formatted string of relevant airport information
        """
        if not self.airports_data or not countries:
            return ""

        # Always include major international hubs (globally distributed)
        major_hubs = [
            # Europe
            "LHR", "CDG", "AMS", "FRA", "MAD", "FCO", "IST",
            # Middle East
            "DXB", "DOH", "AUH",
            # Asia Pacific
            "SIN", "HKG", "BKK", "NRT", "ICN", "SYD",
            # North America
            "JFK", "LAX", "ORD", "DFW", "ATL",
            # Africa
            "JNB", "CAI", "ADD", "NBO", "CPT",
            # South America
            "GRU", "EZE", "BOG"
        ]

        relevant_airports = []

        # Get airports from mentioned countries
        for airport in self.airports_data:
            # Include if airport is in mentioned country or is a major hub
            if airport['country'] in countries or airport['iata_code'] in major_hubs:
                relevant_airports.append(airport)

        # Limit to top 30 by links_count to avoid token overflow
        # For multi-country itineraries, this ensures we get only the busiest/most important airports
        relevant_airports.sort(key=lambda x: x.get('links_count', 0), reverse=True)
        relevant_airports = relevant_airports[:30]

        # Format airport information (condensed to save tokens)
        airport_lines = []
        for airport in relevant_airports:
            # Condensed format: CODE - City, Country
            line = f"{airport['iata_code']} - {airport['city']}, {airport['country']}"
            airport_lines.append(line)

        if airport_lines:
            return "\n⚠️ AIRPORTS (use correct codes):\n" + "\n".join(airport_lines)

        return ""

    async def scrape_page(self, url: str, headless: bool = True) -> dict:
        """
        Scrape itinerary data from a Safari Portal page.

        Args:
            url: The URL of the itinerary page to scrape
            headless: Whether to run browser in headless mode

        Returns:
            Dictionary containing raw scraped data
        """
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=headless)
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            )
            page = await context.new_page()

            try:
                # Navigate to the page and wait for content
                await page.goto(url, wait_until='networkidle', timeout=60000)

                # Wait for the main container to load
                await page.wait_for_selector('#LANDING_PAGES_CONTAINER_ID', timeout=30000)

                # Scroll to load all lazy-loaded content
                await self._scroll_page(page)

                # Extract all the data
                raw_data = await self._extract_data(page)

                return raw_data

            finally:
                await browser.close()

    async def _scroll_page(self, page: Page):
        """Scroll through page to trigger lazy loading."""
        previous_height = 0
        while True:
            current_height = await page.evaluate('document.body.scrollHeight')
            if current_height == previous_height:
                break
            previous_height = current_height
            await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
            await asyncio.sleep(0.5)
        # Scroll back to top
        await page.evaluate('window.scrollTo(0, 0)')

    async def _extract_data(self, page: Page) -> dict:
        """Extract all relevant data from the page."""

        data = {
            'metadata': {},
            'navigation_items': [],
            'contact_info': {},
            'cover_page': {},
            'overview_at_glance': [],  # PRIORITY: Most accurate daily itinerary data
            'sections': [],
            'images': []
        }

        # Extract metadata from cover page
        data['metadata'] = await self._extract_metadata(page)

        # Extract navigation items (table of contents)
        data['navigation_items'] = await self._extract_navigation(page)

        # Extract contact information
        data['contact_info'] = await self._extract_contact_info(page)

        # Extract cover page content
        data['cover_page'] = await self._extract_cover_page(page)

        # PRIORITY: Extract "Itinerary at a glance" section FIRST
        # This contains the most accurate and structured daily itinerary information
        data['overview_at_glance'] = await self._extract_overview_at_glance(page)

        # Extract all sections/pages
        data['sections'] = await self._extract_sections(page)

        # Extract image URLs
        data['images'] = await self._extract_images(page)

        return data

    async def _extract_metadata(self, page: Page) -> dict:
        """Extract tour metadata from the page."""
        metadata = {}

        # Tour name from headline
        headline = await page.query_selector('.Headline_headline__1VaK6')
        if headline:
            metadata['tour_name'] = await headline.inner_text()

        # Client/group info from subheadline
        subheadline = await page.query_selector('.Subheadline_subheadline__2iDqH span[data-block="true"]')
        if subheadline:
            metadata['client_group'] = await subheadline.inner_text()

        # Travel dates
        travel_dates = await page.query_selector('.TravelDates_text__f0Rfp span[data-block="true"]')
        if travel_dates:
            metadata['travel_dates'] = await travel_dates.inner_text()

        return metadata

    async def _extract_navigation(self, page: Page) -> list:
        """Extract navigation/table of contents items."""
        items = []

        nav_items = await page.query_selector_all('.Item_leftSideItem__3MICs')
        for item in nav_items:
            nav_data = {}

            # Get the title
            text_block = await item.query_selector('.Item_textBlock__3RanP')
            if text_block:
                nav_data['title'] = (await text_block.inner_text()).strip()

            # Get the dates if present
            dates = await item.query_selector('.Item_itemDates__1x5MA')
            if dates:
                date_text = (await dates.inner_text()).strip()
                if date_text:
                    nav_data['dates'] = date_text

            # Get the ID for linking
            link = await item.query_selector('a')
            if link:
                nav_data['id'] = await link.get_attribute('id')

            if nav_data.get('title'):
                items.append(nav_data)

        return items

    async def _extract_contact_info(self, page: Page) -> dict:
        """Extract agent/operator contact information."""
        contact = {}

        # Company name
        company = await page.query_selector('.AgentContactsModalContent_name__2QU_N')
        if company:
            contact['company'] = (await company.inner_text()).strip()

        # Email
        email_link = await page.query_selector('a[href^="mailto:"]')
        if email_link:
            href = await email_link.get_attribute('href')
            contact['email'] = href.replace('mailto:', '')

        # Phone numbers
        phone_links = await page.query_selector_all('a[href^="tel:"]')
        phones = []
        for link in phone_links:
            href = await link.get_attribute('href')
            phones.append(href.replace('tel:', ''))
        if phones:
            contact['phone'] = phones[0] if len(phones) == 1 else phones

        return contact

    async def _extract_cover_page(self, page: Page) -> dict:
        """Extract cover page content."""
        cover = {}

        # Quote/title
        title = await page.query_selector('.CoverPage_title__1LbCk')
        if title:
            cover['quote'] = (await title.inner_text()).strip()

        # Author/subtitle
        subtitle = await page.query_selector('.CoverPage_subtitle__HXqBn')
        if subtitle:
            cover['author'] = (await subtitle.inner_text()).strip()

        return cover

    async def _extract_sections(self, page: Page) -> list:
        """Extract all content sections from the page."""
        sections = []

        # Find all landing page sections
        landing_pages = await page.query_selector_all('.LandingPage_landingWrapper__331-z')

        for landing in landing_pages:
            section = {}

            # Get section name from the name attribute
            name = await landing.get_attribute('name')
            if name:
                section['id'] = name
                section['title'] = name.replace('__', ' ').replace('_', ' ')

            # Extract left side content (images, headlines)
            left_side = await landing.query_selector('.LeftSide_left__23yhX')
            if left_side:
                # Subheadline
                sub = await left_side.query_selector('.Subheadline_subheadline__2iDqH')
                if sub:
                    section['subheadline'] = (await sub.inner_text()).strip()

                # Main headline
                headline = await left_side.query_selector('.Headline_headline__1VaK6')
                if headline:
                    section['headline'] = (await headline.inner_text()).strip()

            # Extract right side content (main content)
            right_side = await landing.query_selector('.RightSide_right__2e6At')
            if right_side:
                # Get all text content
                content = await right_side.inner_text()
                section['content'] = content.strip()

                # Try to extract structured elements
                section['elements'] = await self._extract_section_elements(right_side)

            if section.get('title') or section.get('content'):
                sections.append(section)

        return sections

    async def _extract_section_elements(self, container) -> list:
        """Extract structured elements from a section container."""
        elements = []

        # Extract headings
        headings = await container.query_selector_all('h1, h2, h3, h4, h5, h6')
        for h in headings:
            tag = await h.evaluate('el => el.tagName.toLowerCase()')
            text = await h.inner_text()
            elements.append({'type': tag, 'text': text.strip()})

        # Extract paragraphs
        paragraphs = await container.query_selector_all('p')
        for p in paragraphs:
            text = await p.inner_text()
            if text.strip():
                elements.append({'type': 'paragraph', 'text': text.strip()})

        # Extract lists
        lists = await container.query_selector_all('ul, ol')
        for lst in lists:
            items = await lst.query_selector_all('li')
            list_items = []
            for item in items:
                text = await item.inner_text()
                if text.strip():
                    list_items.append(text.strip())
            if list_items:
                list_type = await lst.evaluate('el => el.tagName.toLowerCase()')
                elements.append({'type': list_type, 'items': list_items})

        return elements

    async def _extract_images(self, page: Page) -> list:
        """Extract all image URLs from the page."""
        images = []

        img_elements = await page.query_selector_all('img')
        for img in img_elements:
            src = await img.get_attribute('src')
            alt = await img.get_attribute('alt')
            if src and 'safariportal' in src:
                images.append({
                    'url': src,
                    'alt': alt or ''
                })

        return images

    async def _extract_overview_at_glance(self, page: Page) -> list:
        """
        Extract the 'Itinerary at a glance' section which contains the most accurate
        daily itinerary information.

        This section (Overview_wrapper) has structured Overview_item elements with:
        - Date ranges (Overview_itemTitle)
        - Detailed descriptions (Overview_itemDesc)
        - Accommodation details
        - Number of nights

        Returns:
            List of overview items with structured data
        """
        overview_items = []

        try:
            # Find the overview wrapper container
            overview_wrapper = await page.query_selector('.Overview_wrapper__1fYDp')

            if not overview_wrapper:
                print("⚠ No 'Itinerary at a glance' section found")
                return overview_items

            # Extract all overview items
            items = await overview_wrapper.query_selector_all('.Overview_item__PULIG')

            print(f"✓ Found {len(items)} overview items in 'Itinerary at a glance' section")

            for item in items:
                overview_item = {}

                # Extract date range (title)
                title_element = await item.query_selector('.Overview_itemTitle___Yaze')
                if title_element:
                    overview_item['date_range'] = (await title_element.inner_text()).strip()

                # Extract all description paragraphs
                desc_elements = await item.query_selector_all('.Overview_itemDesc__2BrRB')
                descriptions = []

                for idx, desc in enumerate(desc_elements):
                    text = (await desc.inner_text()).strip()
                    if text:
                        descriptions.append(text)

                # Parse descriptions based on typical structure:
                # [0] = Main description with activities and transfers
                # [1] = Accommodation (often starts with "Overnight at")
                # [2] = Number of nights (e.g., "2 Nights")

                if descriptions:
                    overview_item['main_description'] = descriptions[0]

                    # Check for accommodation in subsequent descriptions
                    for desc in descriptions[1:]:
                        if 'overnight' in desc.lower() or 'accommodation' in desc.lower():
                            overview_item['accommodation'] = desc
                        elif 'night' in desc.lower() and any(char.isdigit() for char in desc):
                            overview_item['nights'] = desc
                        else:
                            # Additional description text
                            if 'additional_description' not in overview_item:
                                overview_item['additional_description'] = []
                            overview_item['additional_description'].append(desc)

                # Only add if we have meaningful data
                if overview_item.get('date_range') or overview_item.get('main_description'):
                    overview_items.append(overview_item)

            print(f"✓ Extracted {len(overview_items)} structured overview items")

        except Exception as e:
            print(f"⚠ Error extracting 'Itinerary at a glance' section: {e}")

        return overview_items

    def _validate_overview_at_glance(self, overview_items: list) -> dict:
        """
        Validate the 'Itinerary at a glance' section for completeness and accuracy.

        Args:
            overview_items: List of overview items extracted from the page

        Returns:
            Dictionary with validation results including warnings and statistics
        """
        validation = {
            'is_valid': False,
            'item_count': len(overview_items),
            'complete_items': 0,
            'warnings': [],
            'missing_data': []
        }

        if not overview_items:
            validation['warnings'].append("CRITICAL: No 'Itinerary at a glance' data found")
            return validation

        for idx, item in enumerate(overview_items):
            item_num = idx + 1
            is_complete = True

            # Check for date range
            if not item.get('date_range'):
                validation['missing_data'].append(f"Item {item_num}: Missing date range")
                is_complete = False

            # Check for main description
            if not item.get('main_description'):
                validation['missing_data'].append(f"Item {item_num}: Missing main description")
                is_complete = False
            elif len(item.get('main_description', '')) < 50:
                validation['warnings'].append(
                    f"Item {item_num}: Main description seems too short ({len(item.get('main_description', ''))} chars)"
                )

            # Check for accommodation info
            if not item.get('accommodation'):
                validation['warnings'].append(f"Item {item_num}: No accommodation information found")

            # Check for nights info
            if not item.get('nights'):
                validation['warnings'].append(f"Item {item_num}: No nights count found")

            if is_complete:
                validation['complete_items'] += 1

        # Mark as valid if we have at least some complete items
        validation['is_valid'] = validation['complete_items'] > 0

        # Summary
        completeness_ratio = validation['complete_items'] / validation['item_count'] if validation['item_count'] > 0 else 0
        validation['completeness_percentage'] = round(completeness_ratio * 100, 1)

        if validation['is_valid']:
            print(f"✓ Overview validation: {validation['complete_items']}/{validation['item_count']} items complete ({validation['completeness_percentage']}%)")
        else:
            print(f"⚠ Overview validation failed: No complete items found")

        if validation['warnings']:
            print(f"⚠ {len(validation['warnings'])} warnings during overview validation")

        return validation

    def _validate_and_fix_data(self, data: dict) -> dict:
        """
        Validate and fix common data parsing errors.

        Args:
            data: Structured itinerary data

        Returns:
            Validated and corrected data
        """
        validation_warnings = []

        # Validate meal plans match accommodation basis
        if 'inclusions' in data and 'meals' in data['inclusions']:
            meals = data['inclusions'].get('meals', {})
            accommodations = data['inclusions'].get('accommodation', [])

            if isinstance(meals, dict) and 'properties' in meals and isinstance(accommodations, list):
                # Create a lookup for accommodation basis by property name
                acc_basis_lookup = {}
                for acc in accommodations:
                    if isinstance(acc, dict):
                        name = acc.get('name', '').strip()
                        basis = acc.get('basis', '').strip()
                        if name and basis:
                            acc_basis_lookup[name.lower()] = basis

                # Validate and fix meal plans
                for meal_property in meals.get('properties', []):
                    prop_name = meal_property.get('property_name', '').strip()
                    meal_plan = meal_property.get('meal_plan', '').strip()

                    # Check if property exists in accommodations
                    prop_name_lower = prop_name.lower()

                    # Try to find matching accommodation (case-insensitive, fuzzy match)
                    matched_acc = None
                    for acc_name_lower, basis in acc_basis_lookup.items():
                        if acc_name_lower == prop_name_lower or \
                           acc_name_lower in prop_name_lower or \
                           prop_name_lower in acc_name_lower:
                            matched_acc = (acc_name_lower, basis)
                            break

                    if matched_acc:
                        correct_basis = matched_acc[1]

                        # If meal plan doesn't match accommodation basis, fix it
                        if meal_plan.lower() != correct_basis.lower():
                            validation_warnings.append(
                                f"FIXED: {prop_name} meal plan changed from '{meal_plan}' to '{correct_basis}' (matched with accommodation basis)"
                            )
                            meal_property['meal_plan'] = correct_basis

                            # Fix meals_included based on correct plan
                            meal_property['meals_included'] = self._get_meals_for_plan(correct_basis)
                    else:
                        # Property not found in accommodations - warn but don't fix
                        validation_warnings.append(
                            f"WARNING: '{prop_name}' in meals section not found in accommodations list"
                        )

        # Validate dates are in ISO format
        if 'daily_itinerary' in data:
            for day in data.get('daily_itinerary', []):
                date_str = day.get('date', '')
                if date_str:
                    # Check if date is in ISO format (YYYY-MM-DD)
                    import re
                    if not re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
                        validation_warnings.append(
                            f"WARNING: Day {day.get('day')} has invalid date format: '{date_str}' (should be YYYY-MM-DD)"
                        )

        # Validate flight data completeness
        if 'inclusions' in data and 'flights' in data['inclusions']:
            flights = data['inclusions'].get('flights', [])
            if isinstance(flights, list):
                for idx, flight in enumerate(flights):
                    if isinstance(flight, dict):
                        missing_fields = []
                        if not flight.get('airline'):
                            missing_fields.append('airline')
                        if not flight.get('from'):
                            missing_fields.append('from')
                        if not flight.get('to'):
                            missing_fields.append('to')
                        if not flight.get('duration'):
                            missing_fields.append('duration')

                        if missing_fields:
                            validation_warnings.append(
                                f"WARNING: Flight {idx + 1} missing required fields: {', '.join(missing_fields)}"
                            )

        # Validate transfer data completeness
        if 'inclusions' in data and 'transportation' in data['inclusions']:
            transfers = data['inclusions'].get('transportation', {}).get('transfers', [])
            if isinstance(transfers, list):
                for idx, transfer in enumerate(transfers):
                    if isinstance(transfer, dict):
                        missing_fields = []
                        if not transfer.get('from'):
                            missing_fields.append('from')
                        if not transfer.get('to'):
                            missing_fields.append('to')
                        if not transfer.get('vehicle'):
                            missing_fields.append('vehicle')

                        if missing_fields:
                            validation_warnings.append(
                                f"WARNING: Transfer {idx + 1} missing required fields: {', '.join(missing_fields)}"
                            )

        # Validate full board properties consistency between logistics and inclusions
        if 'logistics' in data and 'inclusions' in data:
            # Get full board properties from logistics
            logistics_fb_props = data.get('logistics', {}).get('accommodation_patterns', {}).get('full_board_properties', [])

            # Get full board properties from inclusions.accommodation
            inclusions_accommodations = data.get('inclusions', {}).get('accommodation', [])
            inclusions_fb_props = []

            if isinstance(inclusions_accommodations, list):
                for acc in inclusions_accommodations:
                    if isinstance(acc, dict):
                        basis = acc.get('basis', '').lower()
                        name = acc.get('name', '').strip()
                        if name and ('full board' in basis or 'all inclusive' in basis):
                            inclusions_fb_props.append(name)

            # Get full board properties from inclusions.meals
            meals_fb_props = []
            meals_properties = data.get('inclusions', {}).get('meals', {}).get('properties', [])
            if isinstance(meals_properties, list):
                for meal_prop in meals_properties:
                    if isinstance(meal_prop, dict):
                        meal_plan = meal_prop.get('meal_plan', '').lower()
                        prop_name = meal_prop.get('property_name', '').strip()
                        if prop_name and ('full board' in meal_plan or 'all inclusive' in meal_plan):
                            meals_fb_props.append(prop_name)

            # Compare counts and warn if mismatch
            if len(logistics_fb_props) != len(inclusions_fb_props):
                validation_warnings.append(
                    f"❌ CRITICAL: Full board properties count mismatch! "
                    f"Logistics has {len(logistics_fb_props)} properties, "
                    f"but inclusions.accommodation has {len(inclusions_fb_props)} properties with Full Board basis"
                )
                validation_warnings.append(
                    f"  Logistics full_board_properties: {logistics_fb_props}"
                )
                validation_warnings.append(
                    f"  Inclusions Full Board properties: {inclusions_fb_props}"
                )

            if len(logistics_fb_props) != len(meals_fb_props):
                validation_warnings.append(
                    f"❌ CRITICAL: Full board properties count mismatch! "
                    f"Logistics has {len(logistics_fb_props)} properties, "
                    f"but inclusions.meals has {len(meals_fb_props)} properties with Full Board meal plan"
                )
                validation_warnings.append(
                    f"  Logistics full_board_properties: {logistics_fb_props}"
                )
                validation_warnings.append(
                    f"  Meals Full Board properties: {meals_fb_props}"
                )

            # Also check meal_plan_overview consistency
            meal_plan_overview_fb = data.get('logistics', {}).get('meal_plan_overview', {}).get('full_board_locations', [])
            if len(logistics_fb_props) != len(meal_plan_overview_fb):
                validation_warnings.append(
                    f"❌ CRITICAL: Full board properties inconsistency within logistics! "
                    f"accommodation_patterns.full_board_properties has {len(logistics_fb_props)} items, "
                    f"but meal_plan_overview.full_board_locations has {len(meal_plan_overview_fb)} items"
                )
                validation_warnings.append(
                    f"  accommodation_patterns.full_board_properties: {logistics_fb_props}"
                )
                validation_warnings.append(
                    f"  meal_plan_overview.full_board_locations: {meal_plan_overview_fb}"
                )

        # Log validation warnings
        if validation_warnings:
            print("\n=== VALIDATION WARNINGS ===")
            for warning in validation_warnings:
                print(f"  {warning}")
            print("===========================\n")

        return data

    def _get_meals_for_plan(self, meal_plan: str) -> list:
        """
        Get the correct meals array for a given meal plan.

        Args:
            meal_plan: Meal plan string

        Returns:
            List of included meals
        """
        plan_lower = meal_plan.lower()

        if 'bed' in plan_lower and 'breakfast' in plan_lower:
            return ['Breakfast']
        elif 'half board' in plan_lower:
            return ['Breakfast', 'Dinner']
        elif 'full board' in plan_lower:
            return ['Breakfast', 'Lunch', 'Dinner']
        elif 'all inclusive' in plan_lower:
            return ['Breakfast', 'Lunch', 'Dinner', 'Snacks', 'Beverages']
        else:
            # Default to what was stated
            return ['Breakfast']

    def transform_with_claude(self, raw_data: dict) -> dict:
        """
        Send raw scraped data to LLM APIs for transformation into structured JSON.
        Automatically tries all available models in order until successful.

        Args:
            raw_data: Raw scraped data dictionary

        Returns:
            Structured itinerary JSON
        """
        prompt = self._build_transformation_prompt(raw_data)

        # Define all models to try in order of preference
        all_models = []

        # Add Gemini models if available
        if 'gemini' in self.api_clients:
            all_models.extend([
                ("gemini", "gemini-2.0-flash-exp", 8192),
                ("gemini", "gemini-1.5-flash-002", 8192),
                ("gemini", "gemini-1.5-flash", 8192),
                ("gemini", "gemini-1.5-pro-002", 8192),
                ("gemini", "gemini-exp-1206", 8192),
            ])

        # Add OpenRouter models if available (open-source models)
        # Reduced max_tokens to 8192 to stay within budget constraints
        if 'openrouter' in self.api_clients:
            all_models.extend([
                ("openrouter", "meta-llama/llama-3.3-70b-instruct:free", 8192),  # FREE - Llama 3.3 70B
                ("openrouter", "openai/gpt-oss-120b", 8192),  # GPT-OSS 120B - cost-effective large model
                ("openrouter", "meta-llama/llama-3.1-405b-instruct", 8192),
                ("openrouter", "meta-llama/llama-3.1-70b-instruct", 8192),
                ("openrouter", "deepseek/deepseek-r1", 8192),
                ("openrouter", "qwen/qwen-2.5-72b-instruct", 8192),
                ("openrouter", "microsoft/phi-3-medium-128k-instruct", 8192),
                ("openrouter", "openai/gpt-oss-120b:free", 8192),
                ("openrouter", "openai/gpt-oss-20b:free", 8192),
                ("openrouter", "tngtech/deepseek-r1t2-chimera:free", 8192),
                ("openrouter", "tngtech/deepseek-r1t-chimera:free", 8192),
                ("openrouter", "mistralai/mistral-small-3.1-24b-instruct:free", 8192),
            ])

        # Add Hugging Face models if available
        if 'huggingface' in self.api_clients:
            all_models.extend([
                ("huggingface", "meta-llama/Llama-3.1-70B-Instruct", 8192),
                ("huggingface", "Qwen/Qwen2.5-72B-Instruct", 8192),
                ("huggingface", "deepseek-ai/DeepSeek-R1", 8192),
            ])

        # Add Claude as last resort (most reliable but paid)
        if 'anthropic' in self.api_clients:
            all_models.append(("anthropic", "claude-sonnet-4-20250514", 8192))

        if not all_models:
            return {'error': 'No LLM API keys configured. Please set GEMINI_API_KEY, ANTHROPIC_API_KEY, OPENROUTER_API_KEY, or HUGGINGFACE_API_KEY'}

        # Sort models based on performance using LLMPerformanceTracker
        all_models = self.llm_tracker.get_optimal_model_order(all_models)

        # Try each model until one succeeds
        last_error = None
        for provider, model_name, max_tokens in all_models:
            start_time = datetime.now()
            try:
                print(f"Trying {provider} model: {model_name}...")

                if provider == "gemini":
                    result = self._transform_with_gemini_model(prompt, model_name, max_tokens)
                elif provider == "anthropic":
                    result = self._transform_with_anthropic_model(prompt, model_name, max_tokens)
                elif provider == "openrouter":
                    result = self._transform_with_openrouter_model(prompt, model_name, max_tokens)
                elif provider == "huggingface":
                    result = self._transform_with_huggingface_model(prompt, model_name, max_tokens)
                else:
                    continue

                response_time = (datetime.now() - start_time).total_seconds()

                # Check if transformation was successful
                if 'error' not in result:
                    print(f"✓ Successfully transformed with {provider}/{model_name}")
                    self.llm_tracker.record_attempt(provider, model_name, True, response_time)
                    # Validate and fix data before returning
                    result = self._validate_and_fix_data(result)
                    return result
                else:
                    last_error = result.get('error')
                    print(f"✗ {provider}/{model_name} failed: {last_error}")
                    self.llm_tracker.record_attempt(provider, model_name, False, response_time, error_message=last_error)
                    continue

            except Exception as e:
                response_time = (datetime.now() - start_time).total_seconds()
                last_error = str(e)
                error_str = str(e).lower()
                self.llm_tracker.record_attempt(provider, model_name, False, response_time, error_message=last_error)

                # Check if error is retryable
                if any(keyword in error_str for keyword in [
                    "503", "429", "overloaded", "unavailable", "quota",
                    "resource_exhausted", "rate limit", "timeout", "404"
                ]):
                    print(f"✗ {provider}/{model_name} unavailable: {str(e)[:100]}")
                    continue
                else:
                    # For unexpected errors, log and continue to next model
                    print(f"✗ {provider}/{model_name} error: {str(e)[:100]}")
                    continue

        # All models failed
        return {
            'error': f'All available LLM models failed. Last error: {last_error}. '
                    f'Tried {len(all_models)} models across {len(self.api_clients)} providers.'
        }

    def _transform_with_gemini_model(self, prompt: str, model_name: str, max_tokens: int) -> dict:
        """Transform using a specific Google Gemini model."""
        try:
            from google.genai import types

            gemini_client = self.api_clients.get('gemini')
            if not gemini_client:
                return {'error': 'Gemini client not initialized'}

            response = gemini_client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.1,
                    max_output_tokens=max_tokens,
                )
            )

            response_text = response.text

            # Check if response seems truncated
            is_truncated = (
                not response_text.strip().endswith('}') or
                response_text.count('{') != response_text.count('}')
            )

            if is_truncated:
                return {'error': f'{model_name} response truncated'}

            # Try to parse JSON from the response
            return self._parse_json_response(response_text)

        except Exception as e:
            return {'error': str(e)}

    def _transform_with_anthropic_model(self, prompt: str, model_name: str, max_tokens: int) -> dict:
        """Transform using Anthropic Claude API."""
        try:
            anthropic_client = self.api_clients.get('anthropic')
            if not anthropic_client:
                return {'error': 'Anthropic client not initialized'}

            message = anthropic_client.messages.create(
                model=model_name,
                max_tokens=max_tokens,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )

            # Extract JSON from response
            response_text = message.content[0].text
            return self._parse_json_response(response_text)

        except Exception as e:
            return {'error': str(e)}

    def _transform_with_openrouter_model(self, prompt: str, model_name: str, max_tokens: int) -> dict:
        """Transform using OpenRouter API (for Llama, DeepSeek, Qwen, etc.)."""
        try:
            import requests

            api_key = self.api_clients.get('openrouter')
            if not api_key:
                return {'error': 'OpenRouter API key not configured'}

            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model_name,
                    "messages": [
                        {"role": "user", "content": prompt}
                    ],
                    "max_tokens": max_tokens,
                    "temperature": 0.1,
                },
                timeout=120
            )

            if response.status_code != 200:
                return {'error': f'OpenRouter API error: {response.status_code} - {response.text}'}

            data = response.json()
            response_text = data['choices'][0]['message']['content']
            return self._parse_json_response(response_text)

        except Exception as e:
            return {'error': str(e)}

    def _transform_with_huggingface_model(self, prompt: str, model_name: str, max_tokens: int) -> dict:
        """Transform using Hugging Face Inference API."""
        try:
            import requests

            api_key = self.api_clients.get('huggingface')
            if not api_key:
                return {'error': 'Hugging Face API key not configured'}

            response = requests.post(
                f"https://router.huggingface.co/models/{model_name}",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "inputs": prompt,
                    "parameters": {
                        "max_new_tokens": max_tokens,
                        "temperature": 0.1,
                        "return_full_text": False,
                    }
                },
                timeout=120
            )

            if response.status_code != 200:
                return {'error': f'Hugging Face API error: {response.status_code} - {response.text}'}

            data = response.json()

            # Hugging Face returns different formats depending on the model
            if isinstance(data, list) and len(data) > 0:
                response_text = data[0].get('generated_text', '')
            elif isinstance(data, dict):
                response_text = data.get('generated_text', data.get('text', ''))
            else:
                return {'error': f'Unexpected Hugging Face response format: {data}'}

            return self._parse_json_response(response_text)

        except Exception as e:
            return {'error': str(e)}

    def _parse_json_response(self, response_text: str) -> dict:
        """Parse JSON from LLM response text with multiple fallback strategies."""
        # Try to parse the entire response as JSON
        try:
            return json.loads(response_text)
        except json.JSONDecodeError:
            pass

        # Look for JSON in code blocks with json tag
        try:
            json_match = re.search(r'```json\s*([\s\S]*?)\s*```', response_text)
            if json_match:
                return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass

        # Try without json tag
        try:
            json_match = re.search(r'```\s*([\s\S]*?)\s*```', response_text)
            if json_match:
                return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass

        # Try to find JSON object in the response
        try:
            # Find the first { and last }
            start = response_text.find('{')
            end = response_text.rfind('}')
            if start != -1 and end != -1 and end > start:
                json_str = response_text[start:end+1]
                return json.loads(json_str)
        except json.JSONDecodeError:
            pass

        # All parsing attempts failed
        return {
            'error': 'Failed to parse JSON from response',
            'raw_response': response_text[:500]
        }

    def _build_transformation_prompt(self, raw_data: dict) -> str:
        """Build the prompt for Claude to transform raw data."""

        prompt = """You are a data transformation specialist. I have scraped raw data from a Safari Portal itinerary page.
Transform this into a clean, structured JSON format following the exact schema below.

🚨 MANDATORY STEPS:
1. List ALL properties from daily itinerary with night counts (count days where property appears as overnight accommodation)
2. Determine meal plan per property (B only=Bed&Breakfast, B+D=Half Board, B+L+D=Full Board)
3. Build inclusions FIRST (all properties with basis), then COPY to logistics
4. Validate: logistics property counts MUST match inclusions counts exactly

⚠️ ANTI-HALLUCINATION: Extract ONLY explicitly stated data. NO inference. If missing, use null/[]. Only list items mentioned in source.

🔥 DATA PRIORITY: Use 'overview_at_glance' section as PRIMARY source for daily activities, flights, transfers, accommodation. If conflict, trust overview_at_glance.

⚠️ MEAL PLANS: Count ALL meals across ALL days at property. B only=Bed&Breakfast, B+D=Half Board, B+L+D=Full Board, All+beverages=All Inclusive.

⚠️ EXTRACT ALL PROPERTIES: List ALL unique overnight properties from daily itinerary in inclusions.accommodation[] and inclusions.meals[] FIRST, then COPY to logistics. Counts must match exactly.

LOGISTICS: Extract all flights (each flight separate, include from/to airports+countries, flight_type=International if countries differ/Domestic if same, look for "fly to"/"flight" keywords, DON'T extract ground transfers). Transfer arrangements (vehicle types ONLY if explicitly stated). Accommodation patterns: COPY full_board_properties from inclusions.accommodation where basis=Full Board, COPY bed_breakfast_properties where basis=B&B. Meal plan overview: COPY full_board_locations from accommodation_patterns.full_board_properties, COPY bed_breakfast_locations from accommodation_patterns.bed_breakfast_properties. Documents, timing, emergency contacts.

INCLUSIONS: For each property in inclusions.meals[], meal_plan MUST match basis in inclusions.accommodation[]. Transportation broken into vehicles (description+features) and transfers (each transfer separate). Flights (each separate with airline, from, to, duration). Activities and services with details.

TARGET JSON SCHEMA:
{
  "trip_overview": {
    tour_name: "string",
    dates: "string",
    duration: "string",
    client_group: "string",
    tour_operator: "string",
    "group_size": number,
    "countries_visited": ["string"],
    languages: "string",
    "contact": {
      email: "string",
      phone: "string",
      mobile: "string"
    }
  },

  "🚨🚨🚨 REMINDER BEFORE BUILDING LOGISTICS 🚨🚨🚨": "STOP! Before filling in the logistics section below, verify that you have ALREADY completed the entire inclusions section above with ALL properties from the daily itinerary. The logistics section COPIES data from inclusions - do NOT extract logistics data directly from the source.",

  "logistics": {
    summary: "string",
    "flight_details": {
      overview: "string",
      "arrival": {
        "day": number,
        "date": "YYYY-MM-DD",
        airline: "string",
        flight_number: "string",
        from: "string",
        from_country: "string",
        to: "string",
        to_country: "string",
        flight_type: "string",
        arrival_time: "string",
        notes: "string"
      },
      "internal_flights": [
        {
          "day": number,
          "date": "YYYY-MM-DD",
          airline: "string",
          flight_number: "string",
          from: "string",
          from_country: "string",
          to: "string",
          to_country: "string",
          flight_type: "string",
          departure_time: "string",
          arrival_time: "string",
          duration: "string",
          baggage_limit: "string",
          notes: "string"
        }
      ],
      "departure": {
        "day": number,
        "date": "YYYY-MM-DD",
        airline: "string",
        flight_number: "string",
        from: "string",
        from_country: "string",
        to: "string",
        to_country: "string",
        flight_type: "string",
        departure_time: "string",
        notes: "string"
      },
      "important_considerations": [
        "string (e.g., 'Strict adherence to baggage limits is critical', 'Soft-sided luggage mandatory for Tanzania flights', 'Allow ample time for connections')"
      ]
    },
    "transfer_arrangements": {
      overview: "string",
      airport_transfers: "string",
      inter_lodge_transfers: "string",
      "border_crossings": [
        {
          "day": number,
          "date": "YYYY-MM-DD",
          from_country: "string",
          to_country: "string",
          border_point: "string",
          estimated_time: "string",
          procedures: "string",
          notes: "string"
        }
      ],
      "vehicle_types": ["string (e.g., 'Private coach', '4x4 safari vehicles', 'Minivan')"],
      "important_considerations": ["string (notes about documentation, vehicle changes, etc.)"]
    },
    "accommodation_patterns": {
      overview: "string",
      "early_checkouts": [
        {
          "day": number,
          "date": "YYYY-MM-DD",
          property: "string",
          checkout_time: "string",
          reason: "string"
        }
      ],
      "late_arrivals": [
        {
          "day": number,
          "date": "YYYY-MM-DD",
          property: "string",
          estimated_arrival_time: "string",
          reason: "string"
        }
      ],
      "full_board_properties": ["🚨 COPY from inclusions.accommodation where basis='Full Board' - DO NOT create a new list, COPY the property names from inclusions"],
      "bed_breakfast_properties": ["🚨 COPY from inclusions.accommodation where basis='Bed & Breakfast' - DO NOT create a new list, COPY the property names from inclusions"],
      "important_considerations": ["string (e.g., 'Be prepared for early starts on several days')"]
    },
    "meal_plan_overview": {
      summary: "string",
      "full_board_locations": ["🚨 COPY EXACTLY from accommodation_patterns.full_board_properties above - same array, same values"],
      "bed_breakfast_locations": ["🚨 COPY EXACTLY from accommodation_patterns.bed_breakfast_properties above - same array, same values"],
      "special_dining_experiences": ["string (e.g., 'Hot lunch inside Ngorongoro Crater', 'Lesedi Cultural Village lunch')"],
      beverage_policies: "string",
      "important_considerations": ["string (dietary requirements, payment notes)"]
    },
    "timing_considerations": {
      "early_mornings": ["string (days with early departures)"],
      "long_drives": ["string (e.g., 'Serengeti to Ngorongoro', 'Arusha to Amboseli')"],
      flight_schedules: "string",
      border_crossing_time: "string",
      "other_notes": ["string (additional timing considerations)"]
    },
    "documents_and_preparations": {
      "passports_and_visas": {
        passport_validity: "string",
        "visa_requirements": [
          {
            country: "string",
            "required": boolean,
            process: "string",
            notes: "string"
          }
        ],
        notes: "string"
      },
      "health_requirements": {
        yellow_fever: "string",
        vaccinations: "string",
        malaria_prophylaxis: "string",
        "other_precautions": ["string (insect repellent, sun protection, etc.)"]
      },
      travel_insurance: "string",
      "currency": {
        recommendations: "string",
        restrictions: "string",
        notes: "string"
      },
      "clothing_and_packing": {
        general_guidance: "string",
        "clothing": ["string (specific clothing items with rationale)"],
        "gear": ["string (equipment like binoculars, cameras, flashlights)"],
        "accessories": ["string (adapters, rain gear, etc.)"]
      },
      electrical_adapters: "string",
      luggage_requirements: "string",
      photography_equipment: "string"
    },
    "emergency_contacts": [
      {
        name: "string",
        phone: "string",
        email: "string",
        role: "string",
        availability: "string"
      }
    ]
  },
  "daily_breakdown_summary": [
    {
      "day": number,
      "date": "YYYY-MM-DD",
      title: "string",
      summary: "string",
      "highlights": ["string (key highlights - e.g., 'Big Five game viewing', 'Visit to Maasai village', 'Hot air balloon safari')"],
      distance_traveled: "string",
      accommodation_type: "string",
      meals_included: "string"
    }
  ],
  "daily_itinerary": [
    {
      "day": number,
      "date": "YYYY-MM-DD",
      location: "string",
      "accommodation": {
        name: "string",
        type: "string",
        description: "string",
        room_type: "string",
        room_description: "string",
        "total_rooms": number,
        distance_from_airport: "string"
      },
      "meals": {
        "breakfast": boolean,
        "lunch": boolean,
        "dinner": boolean,
        meal_plan: "string"
      },
      "activities": [
        {
          name: "string",
          type: "string",
          description: "string",
          "details": {
            flight_number: "string",
            from: "string",
            to: "string",
            departure_time: "string",
            arrival_time: "string",
            travel_time: "string",
            vehicle: "string"
          },
          "included": boolean
        }
      ],
      "optional_activities": [
        {
          name: "string",
          description: "string"
        }
      ],
      notes: "string"
    }
  ],

  "🚨🚨🚨 SOURCE OF TRUTH - START HERE FIRST 🚨🚨🚨": "The 'inclusions' section below is the PRIMARY source of truth for ALL accommodation and meal data. Extract EVERY property from the daily itinerary and add it here FIRST with correct meal plans. The logistics section will COPY from here.",

  "inclusions": {
    "accommodation": [
      {
        name: "string",
        "nights": number (🚨 COUNT CAREFULLY: How many days in daily_itinerary have this property as overnight accommodation. If property appears on Day 1, Day 2, Day 3 = 3 nights. DO NOT guess - count the actual days),
        location: "string",
        room_type: "string",
        basis: "string",
        "property_inclusions": ["string (e.g., 'All meals', 'House wines', 'Local spirits', 'Soft drinks', 'Laundry service', 'Game drives', 'Bush walks')"],
        "property_exclusions": ["string (e.g., 'Premium wines', 'Champagne', 'Spa treatments', 'Private vehicle hire', 'Balloon safaris')"]
      }
    ],
    "meals": {
      "properties": [
        {
          property_name: "string",
          meal_plan: "string",
          "meals_included": ["string (list of unique meal types provided across all days - e.g., 'Breakfast', 'Lunch', 'Dinner', 'Afternoon tea', 'Sundowner drinks')"],
          beverages_included: "string",
          special_notes: "string"
        }
      ],
      general_notes: "string",
      "special_experiences": ["string (list special meal experiences like 'Bush dinner under the stars', 'Picnic lunch at Ngorongoro Crater', 'Champagne breakfast after balloon safari', 'Private beach dinner')"]
    },
    "transportation": {
      "vehicles": {
        description: "string",
        "features": ["string (list of features - e.g., 'Pop-up roof', 'Window seats guaranteed', 'Charging ports', 'WiFi', 'Cooler box', 'Binoculars provided')"]
      },
      "transfers": [
        {
          type: "string",
          from: "string",
          to: "string",
          vehicle: "string",
          duration: "string",
          notes: "string"
        }
      ]
    },
    "flights": [
      {
        airline: "string",
        flight_number: "string",
        from: "string",
        from_country: "string",
        to: "string",
        to_country: "string",
        flight_type: "string",
        departure_time: "string",
        arrival_time: "string",
        duration: "string",
        baggage: "string",
        notes: "string"
      }
    ],
    "activities": ["string (detailed activity descriptions - e.g., 'Twice-daily game drives in the Serengeti with professional guides', 'Guided walking safari in South Luangwa with armed rangers', 'Cultural visit to Maasai village with traditional dancing and craft demonstrations', 'Sunset dhow cruise in Zanzibar with refreshments')"],
    "services": ["string (detailed service descriptions - e.g., 'Complimentary laundry service at all lodges', 'Flying Doctors emergency evacuation coverage', '24/7 local support hotline', 'Meet and greet at all airports', 'Porter services at hotels', 'Park entry fees for all national parks and reserves')"]
  },
  "exclusions": ["string"],
  "important_information": {
    "luggage": {
      light_aircraft: "string",
      excess_storage: "string"
    },
    "health": {
      malaria: "string",
      yellow_fever: "string",
      water: "string",
      insurance: "string",
      flying_doctors: "string"
    },
    "tipping_guidelines": {
      porters: "string",
      waiters: "string",
      driver_guide: "string"
    },
    "currency": {
      kenya: "string",
      tanzania: "string",
      south_africa: "string",
      notes: "string"
    },
    "climate": {
      east_africa: "string",
      south_africa: "string"
    },
    "electricity": {
      voltage: "string",
      plugs: "string",
      lodges: "string"
    },
    photography: "string",
    communications: "string"
  }
}

"""
        # Extract countries from raw data for airport filtering
        countries = set()
        if 'destinations' in raw_data:
            for dest in raw_data['destinations']:
                if 'location' in dest:
                    # Try to extract country from location string
                    location = dest['location']
                    # Common patterns: "City, Country" or just "Country"
                    if ',' in location:
                        country = location.split(',')[-1].strip()
                        countries.add(country)
                    else:
                        countries.add(location.strip())

        # Add airport reference if we have countries
        if countries:
            airport_reference = self._get_relevant_airports(list(countries))
            if airport_reference:
                prompt += airport_reference + "\n\n"

        prompt += """
RAW SCRAPED DATA:
"""
        prompt += json.dumps(raw_data, indent=2)

        prompt += """

⚠️ VALIDATION:
- Extract ONLY explicitly stated data (no hallucination)
- Property names in meals MUST match accommodation exactly
- Count meals across ALL days at each property
- Dates in YYYY-MM-DD format
- Follow the TARGET JSON SCHEMA structure above exactly
- Return ONLY valid JSON (no markdown, no explanations)
- Ensure all JSON brackets/braces are properly closed
- Start response with { and end with }
Read carefully and validate your output before returning.
Return ONLY the JSON object, no additional text or explanation."""

        return prompt

    def save_to_mongodb(self, itinerary_data: dict, collection_name: str = 'itineraries') -> str:
        """
        Save the structured itinerary data to MongoDB.

        Args:
            itinerary_data: Structured itinerary JSON
            collection_name: MongoDB collection name

        Returns:
            Inserted document ID
        """
        if not self.mongo_client:
            raise ValueError("MongoDB client not configured")

        # Add metadata
        itinerary_data['_metadata'] = {
            'scraped_at': datetime.utcnow(),
            'version': '1.0'
        }

        # Get the database
        db = self.mongo_client.db
        collection = db[collection_name]

        # Insert the document
        result = collection.insert_one(itinerary_data)

        return str(result.inserted_id)

    async def scrape_and_save(self, url: str, headless: bool = True) -> dict:
        """
        Complete workflow: scrape, transform, and save to MongoDB.

        Args:
            url: The URL to scrape
            headless: Whether to run browser in headless mode

        Returns:
            Dictionary with document ID and summary
        """
        # Step 1: Scrape the page
        raw_data = await self.scrape_page(url, headless)

        # Step 1.5: Validate the 'Itinerary at a glance' section
        overview_validation = self._validate_overview_at_glance(
            raw_data.get('overview_at_glance', [])
        )

        # Log validation results
        if not overview_validation['is_valid']:
            print("⚠ WARNING: Overview validation failed - transformation may be less accurate")
            if overview_validation['missing_data']:
                print(f"  Missing data: {overview_validation['missing_data']}")

        # Step 2: Transform with Claude
        structured_data = self.transform_with_claude(raw_data)

        # Step 3: Save to MongoDB
        doc_id = self.save_to_mongodb(structured_data)

        return {
            'document_id': doc_id,
            'tour_name': structured_data.get('trip_overview', {}).get('tour_name', 'Unknown'),
            'days': len(structured_data.get('daily_itinerary', [])),
            'overview_validation': overview_validation,
            'status': 'success'
        }


# Standalone usage
async def main():
    """Example standalone usage."""
    import pymongo

    # Connect to MongoDB
    mongo_uri = os.getenv('MONGO_URI', 'mongodb://localhost:27017/bookings_db')
    client = pymongo.MongoClient(mongo_uri)

    # Create scraper
    scraper = ItineraryScraper(client)

    # Example URL (replace with actual Safari Portal URL)
    url = "https://example.safariportal.app/itinerary/123"

    try:
        result = await scraper.scrape_and_save(url)
        print(f"Saved itinerary: {result}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        client.close()


if __name__ == '__main__':
    asyncio.run(main())
