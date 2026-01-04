# Form Pages AI Helper - Claude AI Integration
# Location: web_services_product/api-server/services/form_pages_ai_helper.py

import os
import json
import re
from typing import List, Dict, Any, Optional
from anthropic import Anthropic

# Configuration
MODEL = "claude-3-5-haiku-20241022"
MAX_TOKENS = 8192
TEMPERATURE = 0.3

# Pricing per million tokens (Claude Haiku)
PRICE_PER_MILLION_INPUT = 1.00   # $1 per million input tokens
PRICE_PER_MILLION_OUTPUT = 5.00  # $5 per million output tokens


class FormPagesAIHelper:
    """
    AI Helper for Form Pages Locator feature.
    Handles all Claude API calls for form discovery operations.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize AI Helper with Anthropic API key.
        
        Args:
            api_key: Anthropic API key (or from environment)
        """
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Anthropic API key not found. Set ANTHROPIC_API_KEY environment variable "
                "or pass api_key parameter."
            )
        
        self.client = Anthropic(api_key=self.api_key)
        self.model = MODEL
        
        # Cost tracking
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.api_call_count = 0
        
        print(f"[FormPagesAIHelper] Initialized with model: {MODEL}")
    
    def _call_claude(self, prompt: str, system_prompt: str = "") -> str:
        """Call Claude API with text prompt"""
        try:
            messages = [{"role": "user", "content": prompt}]
            
            kwargs = {
                "model": MODEL,
                "max_tokens": MAX_TOKENS,
                "temperature": TEMPERATURE,
                "messages": messages
            }
            
            if system_prompt:
                kwargs["system"] = system_prompt
            
            response = self.client.messages.create(**kwargs)
            
            # Track token usage
            self.api_call_count += 1
            self.total_input_tokens += response.usage.input_tokens
            self.total_output_tokens += response.usage.output_tokens
            
            return response.content[0].text
            
        except Exception as e:
            print(f"[FormPagesAIHelper] Error calling Claude API: {e}")
            raise
    
    def _call_claude_vision(self, prompt: str, screenshot_base64: str, system_prompt: str = "", max_tokens: int = 1000) -> str:
        """Call Claude API with vision (image) support"""
        try:
            content = [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/png",
                        "data": screenshot_base64
                    }
                },
                {
                    "type": "text",
                    "text": prompt
                }
            ]
            
            messages = [{"role": "user", "content": content}]
            
            kwargs = {
                "model": self.model,
                "max_tokens": max_tokens,
                "temperature": 0,
                "messages": messages
            }
            
            if system_prompt:
                kwargs["system"] = system_prompt
            
            response = self.client.messages.create(**kwargs)
            
            # Track token usage
            self.api_call_count += 1
            self.total_input_tokens += response.usage.input_tokens
            self.total_output_tokens += response.usage.output_tokens
            
            return response.content[0].text
            
        except Exception as e:
            print(f"[FormPagesAIHelper] Error calling Claude Vision API: {e}")
            raise
    
    def _extract_json_from_response(self, response: str) -> Any:
        """Extract JSON from Claude response"""
        try:
            # Try direct parse first
            return json.loads(response)
        except json.JSONDecodeError:
            pass
        
        # Try to find JSON in markdown code blocks
        json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', response)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass
        
        # Try to find JSON array or object
        json_match = re.search(r'(\[[\s\S]*\]|\{[\s\S]*\})', response)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass
        
        print(f"[FormPagesAIHelper] Failed to parse JSON from response: {response[:200]}")
        return []
    
    def get_cost_summary(self) -> Dict[str, Any]:
        """Calculate total cost of API usage"""
        input_cost = (self.total_input_tokens / 1_000_000) * PRICE_PER_MILLION_INPUT
        output_cost = (self.total_output_tokens / 1_000_000) * PRICE_PER_MILLION_OUTPUT
        total_cost = input_cost + output_cost
        
        return {
            "api_calls": self.api_call_count,
            "input_tokens": self.total_input_tokens,
            "output_tokens": self.total_output_tokens,
            "total_tokens": self.total_input_tokens + self.total_output_tokens,
            "input_cost": input_cost,
            "output_cost": output_cost,
            "total_cost": total_cost
        }
    
    def reset_cost_tracking(self):
        """Reset cost tracking counters"""
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.api_call_count = 0
    
    # ========== LOGIN/LOGOUT STEPS GENERATION ==========
    
    def generate_login_steps(
        self, 
        page_html: str, 
        screenshot_base64: str, 
        username: str, 
        password: str
    ) -> List[Dict[str, Any]]:
        """
        Generate login automation steps using AI Vision.
        
        Args:
            page_html: HTML of the login page
            screenshot_base64: Base64-encoded screenshot
            username: Username for login
            password: Password for login
            
        Returns:
            List of login steps to execute
        """
        print(f"[FormPagesAIHelper] Generating login steps...")
        
        system_prompt = """You are an expert at analyzing web applications and generating automation steps.
Your task is to identify the login form fields and generate steps to log in."""

        user_prompt = f"""Analyze this login page screenshot and HTML to generate login automation steps.

Username to use: {username}
Password to use: {password}

Look for:
1. Username/email input field
2. Password input field  
3. Login/Submit button

For each element, provide:
- action: "fill" for input fields, "click" for buttons
- selector: CSS selector to find the element (prefer id, then name, then class)
- value: the value to fill (username, password, or empty for click)

IMPORTANT: After the login click, you MUST add 2 verification steps:
1. wait_dom_ready - waits for page to stabilize after login
2. verify_clickables - verifies login succeeded by checking for 3+ clickable elements

Return ONLY a JSON array of steps in order, like:
[
  {{"action": "fill", "selector": "#username", "value": "{username}"}},
  {{"action": "fill", "selector": "#password", "value": "{password}"}},
  {{"action": "click", "selector": "#login-btn", "value": ""}},
  {{"action": "wait_dom_ready", "selector": "", "value": ""}},
  {{"action": "verify_clickables", "selector": "", "value": ""}}
]

IMPORTANT:
- Return ONLY the JSON array, no other text
- Use the most reliable CSS selectors you can find from the HTML
- Every step MUST have action, selector, and value fields
- ALWAYS include the 2 verification steps at the end

HTML:
{page_html}"""

        if screenshot_base64:
            response = self._call_claude_vision(user_prompt, screenshot_base64, system_prompt)
        else:
            response = self._call_claude(user_prompt, system_prompt)
        
        steps = self._extract_json_from_response(response)
        print(f"[FormPagesAIHelper] Generated {len(steps)} login steps")
        return steps
    
    def generate_logout_steps(self, page_html: str, screenshot_base64: str) -> List[Dict[str, Any]]:
        """
        Generate logout automation steps using AI Vision.
        
        Args:
            page_html: HTML of the current page
            screenshot_base64: Base64-encoded screenshot
            
        Returns:
            List of logout steps to execute
        """
        print(f"[FormPagesAIHelper] Generating logout steps...")
        
        system_prompt = """You are an expert at analyzing web applications and generating automation steps.
Your task is to identify the logout button/link and generate steps to log out of the application."""

        user_prompt = """Analyze this page screenshot and HTML to generate logout automation steps.

Look for:
1. User menu/dropdown (usually shows username or profile icon in header/navbar)
2. Logout/Sign out button or link (might be inside a dropdown menu)

Common patterns:
- Click on user avatar/name to open dropdown, then click "Logout"
- Direct "Logout" or "Sign out" link in navigation
- Settings menu with logout option

For each element, provide:
- action: "click" for buttons/links
- selector: CSS selector to find the element (prefer id, then class, then text-based selectors)
- value: empty string "" for click actions

IMPORTANT: After the logout click, you MUST add 2 verification steps:
1. wait_dom_ready - waits for page to stabilize after logout
2. verify_login_page - verifies we're back at the login page (checks for username/password input fields)

Return ONLY a JSON array of steps in order, like:
[
  {"action": "click", "selector": ".user-dropdown", "value": ""},
  {"action": "click", "selector": "a[href*='logout']", "value": ""},
  {"action": "wait_dom_ready", "selector": "", "value": ""},
  {"action": "verify_login_page", "selector": "", "value": ""}
]

IMPORTANT:
- Return ONLY the JSON array, no other text
- Use the most reliable CSS selectors you can find from the HTML
- If logout requires opening a menu first, include that step
- Every step MUST have action, selector, and value fields
- ALWAYS include the 2 verification steps at the end

HTML (truncated):
""" + page_html[:15000]

        if screenshot_base64:
            response = self._call_claude_vision(user_prompt, screenshot_base64, system_prompt)
        else:
            response = self._call_claude(user_prompt, system_prompt)
        
        steps = self._extract_json_from_response(response)
        print(f"[FormPagesAIHelper] Generated {len(steps)} logout steps")
        return steps
    
    # ========== FORM NAME EXTRACTION ==========
    
    def extract_form_name(
        self, 
        context_data: Dict[str, Any], 
        existing_names: List[str] = None
    ) -> str:
        """
        Extract semantic form name using AI.
        
        Args:
            context_data: Dictionary with url, url_path, button_clicked, page_title, headers, form_labels
            existing_names: List of already used form names to avoid duplicates
            
        Returns:
            Clean form name as string
        """
        existing_names = existing_names or []
        
        existing_names_str = ""
        if existing_names:
            existing_names_str = f"\nEXISTING FORM NAMES (don't use these):\n{', '.join(existing_names)}"
        
        context_str = f"""URL: {context_data.get('url', '')}
URL Path: {context_data.get('url_path', '')}
Button Clicked: {context_data.get('button_clicked', '')}
Page Title: {context_data.get('page_title', '')}
Headers: {', '.join(context_data.get('headers', [])) if context_data.get('headers') else 'None'}
Form Labels: {', '.join(context_data.get('form_labels', [])) if context_data.get('form_labels') else 'None'}{existing_names_str}"""

        prompt = f"""You are analyzing a form page to determine its proper name for a test automation framework.

Context about the page:
{context_str}

Based on this context, what is the BEST name for this form?

Rules:
1. Focus on the ENTITY (thing) being managed, NOT the action
   - ✅ Good: "Employee", "Leave_Type", "Performance_Review"
   - ❌ Bad: "Employee_Search", "Leave_Type_List", "Search_Performance"

2. Remove action/operation words:
   - Remove: search, view, list, add, create, edit, update, delete, manage, management, configure, configuration, define, tracker, log
   - Exception: Keep action words ONLY if they're part of the entity name itself (e.g., "Leave_Entitlement")

3. Simplify compound names:
   - "performance_tracker_log" → "Performance"
   - "candidate_search" → "Candidate"  
   - "system_users_admin" → "System_User"
   - "leave_type_list" → "Leave_Type"

4. Use Title_Case_With_Underscores (e.g., "Performance_Review", "Leave_Type")

5. Use singular or plural based on context:
   - For forms managing ONE item: use singular (e.g., "Employee", "Project")
   - For forms managing LISTS/MULTIPLE: keep plural if it's the entity name (e.g., "Leave_Entitlements" if that's the actual feature name)

6. Be concise: 1-3 words maximum

7. Remove technical suffixes: .htm, .php, _page, _form, etc.

8. Choose a name that does NOT exist in EXISTING FORM NAMES list above

Examples:
- URL: /employee/search → Name: "Employee"
- URL: /performance/tracker/log → Name: "Performance"
- URL: /leave/types/list → Name: "Leave_Type"
- URL: /candidate/view → Name: "Candidate"

Respond with ONLY the form name, nothing else.

Form name:"""

        response = self._call_claude(prompt)
        form_name = response.strip().lower().strip('"\'` ')
        
        print(f"[FormPagesAIHelper] Extracted form name: '{form_name}'")
        return form_name
    
    # ========== PARENT REFERENCE FIELDS ==========
    
    def extract_parent_reference_fields(
        self, 
        form_name: str, 
        page_html: str, 
        screenshot_base64: str = None
    ) -> List[Dict[str, Any]]:
        """
        Extract parent reference fields from form using AI.
        
        Args:
            form_name: Name of the form being analyzed
            page_html: HTML of the form page
            screenshot_base64: Optional screenshot for vision analysis
            
        Returns:
            List of parent reference field dictionaries
        """
        print(f"[FormPagesAIHelper] Extracting parent reference fields for: {form_name}")

        system_prompt = """You are an expert at analyzing web forms to identify parent reference fields.
You MUST analyze BOTH the screenshot AND the HTML DOM thoroughly. Do not skip any potential parent field."""

        user_prompt = f"""Analyze this form THOROUGHLY to identify ALL parent reference fields.

Form name: {form_name}

IMPORTANT INSTRUCTIONS:
1. Analyze BOTH the screenshot AND the HTML DOM carefully
2. Do NOT skip any potential parent field - be comprehensive
3. Look for ALL patterns, not just obvious dropdowns
4. ONLY include fields that are INSIDE the form - ignore navigation, headers, sidebars, filters, and other page elements
5. Focus on the main form area visible in the screenshot

WHAT TO LOOK FOR:

1. SELECT/DROPDOWN fields:
   - <select> elements with options
   - Fields labeled "Select...", "Choose..."

2. AUTOCOMPLETE/TYPEAHEAD fields:
   - Inputs with autocomplete functionality
   - Fields with search/lookup icons
   - data-autocomplete, aria-autocomplete attributes

3. LOOKUP/REFERENCE fields:
   - Input + button combinations for searching
   - Fields with magnifying glass icons
   - "Browse...", "Search...", "Find..." buttons

4. HIDDEN ID fields paired with visible name fields:
   - <input type="hidden" name="*_id">
   - Read-only text showing selected entity name

5. COMMON NAMING PATTERNS:
   - *_id, *_code fields
   - Fields referencing: Employee, Department, Project, Category, Type, Status, Account, Customer, Vendor, etc.

6. VISUAL CLUES IN SCREENSHOT:
   - Dropdown arrows
   - Search icons
   - Lookup buttons
   - Fields showing "Select..." placeholder

Return a JSON array of ALL parent reference fields found:
[
  {{"field_name": "employee_id", "field_label": "Select Employee", "parent_entity": "Employee", "field_type": "dropdown"}},
  {{"field_name": "department", "field_label": "Department", "parent_entity": "Department", "field_type": "autocomplete"}}
]

field_type should be one of: dropdown, autocomplete, lookup, hidden_id, select

If no parent reference fields found, return: []

Be THOROUGH - missing a parent field will break the hierarchy!

HTML DOM:
{page_html}

Return ONLY the JSON array:"""

        if screenshot_base64:
            response = self._call_claude_vision(user_prompt, screenshot_base64, system_prompt, max_tokens=2000)
        else:
            response = self._call_claude(user_prompt, system_prompt)
        
        fields = self._extract_json_from_response(response)
        print(f"[FormPagesAIHelper] Found {len(fields)} parent reference fields")
        return fields
    
    # ========== UI DEFECT VERIFICATION ==========
    
    def verify_ui_defects(self, form_name: str, screenshot_base64: str) -> str:
        """
        Analyze form screenshot for UI defects using AI Vision.
        
        Args:
            form_name: Name of the form being analyzed
            screenshot_base64: Base64-encoded screenshot of the form page
            
        Returns:
            String describing defects found, or empty string if none
        """
        print(f"[FormPagesAIHelper] Verifying UI for defects on form: {form_name}")
        
        if not screenshot_base64:
            print(f"[FormPagesAIHelper] No screenshot provided for UI verification")
            return ""
        
        system_prompt = """You are a test automation expert performing UI verification."""
        
        user_prompt = """Analyze this screenshot for visual defects.

**SYSTEMATIC SCAN:**

1. Check page corners (top-left, top-right, bottom-left, bottom-right)
2. Check background area around form container
3. Check each form field for unexpected borders, boxes, or artifacts

**What to Look For:**
- Overlapping elements
- Unexpected overlays blocking elements
- Broken layout or misaligned elements
- Visual artifacts (unexpected colored boxes, shapes, borders)
- Styling defects (corrupted borders, inconsistent colors)
- Elements floating outside containers

**If NO defects found, respond with:** "No defects detected"

**If defects found:** Describe each defect and its location.

Your response:"""

        response = self._call_claude_vision(user_prompt, screenshot_base64, system_prompt, max_tokens=500)
        
        if "no defects detected" in response.lower():
            return ""
        
        return response.strip()
    
    # ========== BUTTON CLASSIFICATION ==========
    
    def is_submission_button(self, button_text: str, screenshot_base64: str = None) -> bool:
        """
        Determine if button indicates this is a form page (submission or multi-step form).
        
        Args:
            button_text: Text on the button
            screenshot_base64: Optional screenshot for visual context
            
        Returns:
            True if form page indicator, False otherwise
        """
        # If screenshot provided, use vision for better accuracy
        if screenshot_base64:
            prompt = f"""You are analyzing a web page screenshot to determine if it contains a FORM PAGE.

Button text found: "{button_text}"

Look at the screenshot and determine:
1. Does this page have input fields (text boxes, dropdowns, checkboxes, etc.)?
2. Look at the area around the button "{button_text}" - if there are search/filter fields with a 'Search' button nearby, this is a SEARCH page, NOT a form page.
3. Is the button "{button_text}" a submission button for a form that collects data?

✅ FORM PAGE INDICATORS (answer YES):
- Page has visible input fields AND a submission button like 'Submit', 'Save', 'Update', 'Confirm', 'Apply', 'Send'
- Page has visible input fields AND a multi-step button like 'Next', 'Continue', 'Proceed'

❌ NOT FORM PAGE INDICATORS (answer NO):
- No input fields visible on the page
- Button opens/navigates to a NEW form: 'Add', 'Create', 'New', 'Insert', 'Register', '添加', '新建', '创建'
- SEARCH/FILTER forms with buttons like 'Search', 'Find', 'Filter', 'Go', 'Reset', '搜索', '重置', '查询'
- Login forms (username + password + login button)
- Cancel, Back, Close buttons
- Pages with a data table/grid below the input fields (likely a SEARCH page)
- LIST PAGES that show existing records with an 'Add' button to create new ones
- If you see "(X) Records Found" or a table of existing data, this is a LIST page, NOT a form page

Question: Is this a form page with a submission button?
Answer ONLY 'yes' or 'no'."""

            response = self._call_claude_vision(prompt, screenshot_base64, max_tokens=10)
            answer = response.strip().upper()
            is_submission = answer.startswith("YES")
            
            print(f"[FormPagesAIHelper] Button '{button_text}' + screenshot → {'submission' if is_submission else 'navigation'}")
            return is_submission
        
        # No screenshot - use text-only prompt (original logic)
        prompt = f"""You are analyzing a button on a web page to determine if it indicates this is a FORM PAGE.
            Button text: "{button_text}"
            
            CRITICAL: We want to identify if this page contains a form that collects user input.
            
            ✅ FORM PAGE INDICATORS (answer YES):
            - Submission buttons: 'Submit', 'Save', 'Update', 'Confirm', 'Apply', 'Send'
            - Multi-step form buttons: 'Next', 'Continue', 'Proceed', 'Forward', 'Step'
            - These buttons indicate the page has a form collecting data
            
            ❌ NOT FORM PAGE INDICATORS (answer NO):
            - Buttons that OPEN/NAVIGATE to a NEW form: 'Add', 'Create', 'New', 'Insert', 'Register'
            - SEARCH/FILTER buttons: 'Search', 'Find', 'Filter', 'Go', 'Reset'
            - Login buttons: 'Login', 'Sign In', 'Log In'
            - Cancel, Back, Close buttons
            - Navigation links
            
            Question: Does this button indicate the current page IS a form (collecting data)?
            Answer ONLY 'yes' or 'no'."""
        
        response = self.client.messages.create(
            model="claude-3-5-haiku-20241022",
            max_tokens=10,
            temperature=0,
            messages=[{"role": "user", "content": prompt}]
        )
        
        # Track usage
        self.api_call_count += 1
        self.total_input_tokens += response.usage.input_tokens
        self.total_output_tokens += response.usage.output_tokens
        
        answer = response.content[0].text.strip().upper()
        is_submission = answer.startswith("YES")
        
        print(f"[FormPagesAIHelper] Button '{button_text}' → {'submission' if is_submission else 'navigation'}")
        return is_submission
    
    def get_navigation_clickables(self, screenshot_base64: str) -> List[str]:
        """Ask AI to identify all navigation clickables in screenshot"""
        if not screenshot_base64:
            return []
        
        prompt = """Look at this web application screenshot and identify ALL clickable elements that are used for NAVIGATION to different pages/sections.

INCLUDE these types of clickables:
- Main menu items and navigation links
- Sidebar menu items
- Tab headers
- "Add", "New", "Create" buttons that open forms
- Dropdown menu triggers
- Card/tile links that navigate to detail pages
- Action buttons in toolbars
- If you see an open/expanded dropdown menu, include all its visible items

EXCLUDE these (do NOT include):
- Table row data or cells
- Pagination controls (page numbers, next/prev)
- Search/filter buttons and inputs
- Sort buttons in table headers
- User profile/logout buttons
- Close/Cancel/Back buttons
- Checkboxes, radio buttons, form inputs
- Elements that appear to be part of data display
- ANY item that appears as one of many similar rows in a vertical list
- Expandable/collapsible rows that show details when clicked
- CRITICAL - If you see multiple items stacked vertically with similar styling, they are NOT navigation


Return ONLY a JSON array of the visible text labels for navigation clickables.
Example: ["Dashboard", "Users", "Add Employee", "Reports", "Settings", "PIM", "Leave"]

IMPORTANT: Return ONLY the JSON array, no explanation or markdown."""

        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=500,
                temperature=0,
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": screenshot_base64
                            }
                        },
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ]
                }]
            )
            
            # Track usage
            self.api_call_count += 1
            self.total_input_tokens += response.usage.input_tokens
            self.total_output_tokens += response.usage.output_tokens
            
            # Parse response
            response_text = response.content[0].text.strip()
            
            # Handle markdown code blocks
            if response_text.startswith("```"):
                lines = response_text.split("\n")
                response_text = "\n".join(lines[1:-1])
            
            import json
            clickables = json.loads(response_text)
            
            print(f"[FormPagesAIHelper] AI identified {len(clickables)} navigation clickables")
            return clickables
            
        except Exception as e:
            print(f"[FormPagesAIHelper] Error getting navigation clickables: {e}")
            return []

    def build_form_hierarchy(
            self,
            forms_data: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Build parent-child hierarchy for all form pages using AI.

        Args:
            forms_data: List of form data, each containing:
                - form_name: Name of the form
                - form_id: Database ID
                - parent_fields: List of parent reference fields found

        Returns:
            List of hierarchy relationships:
            [{"form_id": 1, "form_name": "Finding", "parent_form_id": 2, "parent_form_name": "Engagement"}, ...]
        """
        if not forms_data:
            return []

        print(f"[FormPagesAIHelper] Building hierarchy for {len(forms_data)} forms using AI...")

        # Build form list for prompt
        forms_summary = []
        for form in forms_data:
            parent_fields_str = ", ".join([
                f.get("parent_entity", f.get("field_label", "unknown"))
                for f in form.get("parent_fields", [])
            ]) or "none"
            forms_summary.append(
                f"- {form['form_name']} (id={form['form_id']}): parent_fields=[{parent_fields_str}]")

        forms_list = "\n".join(forms_summary)

        system_prompt = """You are an expert at analyzing web application data models and determining parent-child relationships between forms/entities."""

        user_prompt = f"""Analyze these form pages and their parent reference fields to build a complete parent-child hierarchy.

FORMS DISCOVERED:
{forms_list}

RULES:
1. A form with a parent_field referencing another entity is a CHILD of that entity's form
2. Example: "Finding" form has parent_field "Engagement" → Finding is child of Engagement
3. Forms with no parent_fields are ROOT forms (parent_form_id = null)
4. Match parent_field names to form names intelligently (e.g., "Employee" field matches "Employees" or "Employee_Management" form)
5. A form can only have ONE parent (if multiple parent_fields exist, choose the most logical primary parent)

Return a JSON array with the hierarchy:
[
  {{"form_id": <id>, "form_name": "<name>", "parent_form_id": <parent_id_or_null>, "parent_form_name": "<parent_name_or_null>"}},
  ...
]

Include ALL forms in the response, even root forms with parent_form_id: null.

Return ONLY the JSON array:"""

        response = self._call_claude(user_prompt, system_prompt)
        hierarchy = self._extract_json_from_response(response)

        print(f"[FormPagesAIHelper] AI built hierarchy with {len(hierarchy)} relationships")
        return hierarchy