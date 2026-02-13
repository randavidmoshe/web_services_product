# ai_form_mapper_main_prompter.py
# AI-Powered Test Step Generation using Claude API

import json
import time
import logging
import anthropic
import random
from typing import List, Dict, Optional, Any
from anthropic._exceptions import OverloadedError, APIError

class AIParseError(Exception):
    """Raised when AI response cannot be parsed after all retries"""
    pass

logger = logging.getLogger('init_logger.form_page_test')
result_logger_gui = logging.getLogger('init_result_logger_gui.form_page_test')


class AIHelper:
    """Helper class for AI-powered step generation using Claude API"""
    
    def __init__(self, api_key: str, session_logger=None):
        if not api_key:
            raise ValueError("API key is required for AI functionality")
        self.client = anthropic.Anthropic(api_key=api_key)
        #self.model = "claude-sonnet-4-5-20250929"
        self.model = "claude-haiku-4-5-20251001"
        self.session_logger = session_logger  # For debug mode logging
    
    def _call_api_with_retry(self, prompt: str, max_tokens: int = 16000, max_retries: int = 3) -> Optional[str]:
        """
        Call Claude API with retry logic for handling overload errors
        
        Args:
            prompt: The prompt to send
            max_tokens: Maximum tokens for response
            max_retries: Number of retry attempts (default: 3)
            
        Returns:
            Response text or None if all retries fail
        """
        delay = 2  # Start with 2 second delay
        
        for attempt in range(max_retries):
            try:
                print(f"[AIHelper] Calling Claude API (attempt {attempt + 1}/{max_retries})...")
                result_logger_gui.info(f"[AIHelper] Calling Claude API (attempt {attempt + 1}/{max_retries})...")
                
                message = self.client.messages.create(
                    model=self.model,
                    max_tokens=max_tokens,
                    messages=[
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ]
                )
                
                response_text = message.content[0].text
                print(f"[AIHelper] ✅ API call successful ({len(response_text)} chars)")
                return response_text
                
            except OverloadedError as e:
                if attempt == max_retries - 1:
                    # Last attempt failed
                    print(f"[AIHelper] ❌ API Overloaded after {max_retries} attempts. Giving up.")
                    logger.error(f"[AIHelper] API Overloaded after {max_retries} attempts: {e}")
                    raise AIParseError(f"API Overloaded after {max_retries} attempts: {e}")
                
                # Add jitter to prevent thundering herd
                jitter = random.uniform(0, delay * 0.5)
                wait_time = delay + jitter
                
                print(f"[AIHelper] ⚠️  API Overloaded (529). Retrying in {wait_time:.1f}s... ({attempt + 1}/{max_retries})")
                logger.warning(f"[AIHelper] API Overloaded. Retry {attempt + 1}/{max_retries} after {wait_time:.1f}s")
                
                time.sleep(wait_time)
                delay *= 2  # Exponential backoff
                
            except APIError as e:
                if attempt == max_retries - 1:
                    print(f"[AIHelper] ❌ API Error after {max_retries} attempts: {e}")
                    logger.error(f"[AIHelper] API Error after {max_retries} attempts: {e}")
                    raise AIParseError(f"API Error after {max_retries} attempts: {e}")
                
                print(f"[AIHelper] ⚠️  API Error: {e}. Retrying in {delay}s... ({attempt + 1}/{max_retries})")
                logger.warning(f"[AIHelper] API Error. Retry {attempt + 1}/{max_retries} after {delay}s")
                
                time.sleep(delay)
                delay *= 2
                
            except Exception as e:
                print(f"[AIHelper] ❌ Unexpected error: {e}")
                logger.error(f"[AIHelper] Unexpected error: {e}")
                raise AIParseError(f"Unexpected API error: {e}")
        
        raise AIParseError("API call failed after all retries")
    
    def _call_api_with_retry_multimodal(self, content: list, max_tokens: int = 16000, max_retries: int = 3) -> Optional[str]:
        """
        Call Claude API with retry logic for multimodal content (images + text)
        
        Args:
            content: List of content blocks (can include images and text)
            max_tokens: Maximum tokens for response
            max_retries: Number of retry attempts (default: 3)
            
        Returns:
            Response text or None if all retries fail
        """
        delay = 2  # Start with 2 second delay
        
        for attempt in range(max_retries):
            try:
                print(f"[AIHelper] Calling Claude API with vision for steps generation (attempt {attempt + 1}/{max_retries})...")
                result_logger_gui.info(f"[AIHelper] Calling Claude API with vision for steps generation (attempt {attempt + 1}/{max_retries})...")
                
                message = self.client.messages.create(
                    model=self.model,
                    max_tokens=max_tokens,
                    messages=[
                        {
                            "role": "user",
                            "content": content
                        }
                    ]
                )
                
                response_text = message.content[0].text
                print(f"[AIHelper] ✅ API call successful ({len(response_text)} chars)")
                return response_text
                
            except OverloadedError as e:
                if attempt == max_retries - 1:
                    print(f"[AIHelper] ❌ API Overloaded after {max_retries} attempts. Giving up.")
                    logger.error(f"[AIHelper] API Overloaded after {max_retries} attempts: {e}")
                    raise AIParseError(f"API Overloaded after {max_retries} attempts: {e}")
                
                jitter = random.uniform(0, delay * 0.5)
                wait_time = delay + jitter
                
                print(f"[AIHelper] ⚠️  API Overloaded (529). Retrying in {wait_time:.1f}s... ({attempt + 1}/{max_retries})")
                logger.warning(f"[AIHelper] API Overloaded. Retry {attempt + 1}/{max_retries} after {wait_time:.1f}s")
                
                time.sleep(wait_time)
                delay *= 2
                
            except APIError as e:
                if attempt == max_retries - 1:
                    print(f"[AIHelper] ❌ API Error after {max_retries} attempts: {e}")
                    logger.error(f"[AIHelper] API Error after {max_retries} attempts: {e}")
                    raise AIParseError(f"API Error after {max_retries} attempts: {e}")
                
                print(f"[AIHelper] ⚠️  API Error: {e}. Retrying in {delay}s... ({attempt + 1}/{max_retries})")
                logger.warning(f"[AIHelper] API Error. Retry {attempt + 1}/{max_retries} after {delay}s")
                
                time.sleep(delay)
                delay *= 2
                
            except Exception as e:
                print(f"[AIHelper] ❌ Unexpected error: {e}")
                logger.error(f"[AIHelper] Unexpected error: {e}")
                raise AIParseError(f"Unexpected API error: {e}")
        
        raise AIParseError("API call failed after all retries")

    def generate_test_steps(
            self,
            dom_html: str,
            test_cases: List[Dict[str, str]],
            screenshot_base64: Optional[str] = None,
            critical_fields_checklist: Optional[Dict[str, str]] = None,
            field_requirements: Optional[str] = None,
            junction_instructions: Optional[str] = None,
            user_provided_inputs: Optional[Dict] = None,
            # Legacy params - kept for backward compatibility with callers
            previous_steps: Optional[List[Dict]] = None,
            step_where_dom_changed: Optional[int] = None,
            test_context=None,
            is_first_iteration: bool = False,
            mapping_hints: str = ""
    ) -> Dict[str, Any]:
        """
        Generate Selenium test steps based on DOM and test cases.

        Returns:
            Dict with 'steps' (list), 'ui_issue' (string), and 'no_more_paths' (bool)
        """

        if self.session_logger:
            self.session_logger.info("🤖 !*!*!* Entering FORM MAPPER prompter: generate_test_steps", category="ai_routing")

        # Build UI verification section - simplified intro without UI verification task
        ui_task_section = "You are a test automation expert. Your task is to generate Selenium WebDriver test steps for the form page.\n\n"

        # Mapping hints from user
        hints_section = f"## AI GUIDANCE NOTES FROM USER\n{mapping_hints}\n\n" if mapping_hints else ""
        
        # Build critical fields checklist section (for Scenario B recovery)
        critical_fields_section = ""
        if critical_fields_checklist:
            fields_list = "\n".join([f"- **{field_name}**: {issue_type}" for field_name, issue_type in critical_fields_checklist.items()])
            
            # Include AI rewritten requirements if available
            requirements_text = ""
            if field_requirements:
                requirements_text = f"""
**EXACT REQUIREMENTS FROM ALERT:**
{field_requirements}
"""
            
            critical_fields_section = f"""
⚠️⚠️⚠️ CRITICAL FIELDS CHECKLIST ⚠️⚠️⚠️
================================================================================
**ALERT RECOVERY MODE ACTIVE**

A validation alert was detected. The following fields MUST be filled correctly:

{fields_list}
{requirements_text}
**MANDATORY INSTRUCTIONS:**
1. Pay SPECIAL ATTENTION to these critical fields
2. For fields marked "MUST FILL" - ensure they are filled with correct values from test_cases
3. For fields marked "INVALID FORMAT" - use the correct format/value from test_cases
4. These fields caused the previous test failure - DO NOT skip them!
5. Verify the selectors for these fields are correct
6. Double-check the values match test_cases exactly

This checklist will remain active until the test completes successfully.
================================================================================

"""

        # Junction instructions for multi-path discovery
        route_planning_section = ""
        if junction_instructions:
            route_planning_section = f"""
🔀 JUNCTION INSTRUCTIONS:
{junction_instructions}

When you have a step for these junctions, use the specified option. If a junction doesn't exist in the current form state, skip it.


"""
        # User-provided inputs section
        user_inputs_section = ""

        # Check for test scenario content (raw text)
        if user_provided_inputs and user_provided_inputs.get("content") and user_provided_inputs.get(
                "source") == "test_scenario":
            scenario_name = user_provided_inputs.get("scenario_name", "Test Scenario")
            content = user_provided_inputs.get("content", "")
            user_inputs_section = f"""
📋 TEST SCENARIO: {scenario_name}
{'=' * 60}
Use these field values when filling the form:

{content}

{'=' * 60}
"""
        elif user_provided_inputs and (
                user_provided_inputs.get("field_values") or user_provided_inputs.get("file_paths")):
            field_values = user_provided_inputs.get("field_values", [])
            file_paths = user_provided_inputs.get("file_paths", [])

            lines = ["📋 USER-PROVIDED INPUTS (MANDATORY)", "=" * 60,
                     "Use these EXACT values when filling matching fields:", ""]

            if field_values:
                lines.append("FIELD VALUES:")
                for fv in field_values:
                    lines.append(f"- {fv.get('field_hint', 'unknown')} → {fv.get('value', '')}")
                lines.append("")

            if file_paths:
                lines.append("FILE PATHS (use for file upload fields):")
                for fp in file_paths:
                    lines.append(f"- {fp.get('field_hint', 'unknown')} → {fp.get('path', '')}")
                lines.append("")

            lines.extend(["=" * 60, ""])
            user_inputs_section = "\n".join(lines)

        # Screenshot emphasis section
        screenshot_section = ""
        if screenshot_base64:
            screenshot_section = """
            🖼️ SCREENSHOT PROVIDED - FOR VISUAL CONTEXT
            ================================================================================
            Use the screenshot to understand:
            - Which tab/section is currently active
            - Visual layout and what's currently visible
            - Any modals, overlays, or popups shown

            **IMPORTANT:** The screenshot only shows the visible viewport - there may be MORE 
            fields in scrollable areas that you can't see in the image but ARE in the DOM.
            Always check the DOM for the complete list of fields - the screenshot is just 
            a visual aid, not the complete picture!
            ================================================================================

            """

        prompt = f"""{ui_task_section}
{hints_section}{screenshot_section}
{critical_fields_section}
{route_planning_section}
{user_inputs_section}
        === SELECTOR GUIDELINES ===
        
        **CRITICAL THE LOCATOR MUST SUCCEED - IF IN DOUBT → USE XPATH **
        
        **Use CSS selectors (RECOMMENDED):**
           ✅ input[name='email']                           ← Good: form attributes
           ✅ input[data-qa='username-input']               ← Best: unique data attributes
           ✅ #email-field                                  ← Good: unique ID
           ✅ select[name='country']                        ← Good: dropdowns
           ✅ .submit-button                                ← Good: IF unique on page
        
        ** or buttons like accept/save/submit/ok use unique locators as most look alike  - so maybe XPATH for them
        
        **General Priority (for any element):**
           Priority 1: data-qa, data-testid, data-test attributes
           Priority 2: name, type, id attributes
           Priority 3: Unique IDs or classes
           Priority 4: Structural selectors (last resort)
           
        

        **FORBIDDEN SYNTAX (Playwright/jQuery specific):**
           ❌ :has-text('text')           ← Playwright only - NOT in Selenium
           ❌ :contains('text')            ← jQuery only - NOT in Selenium  
           ❌ :text('text')                ← Playwright only - NOT in Selenium
           ❌ >> (combinator)              ← Playwright only - NOT in Selenium

        **Good Examples:**

        

        Input Fields:
        ✅ "selector": "input[name='email']"
        ✅ "selector": "input[data-qa='username-input']"
        ✅ "selector": "#password-field"

        Links:
        ✅ "selector": "a[href='/terms']"
        ✅ "selector": "a.privacy-link"

        Dropdowns:
        ✅ "selector": "select[name='country']"
        ✅ "selector": "#state-dropdown"
        ✅ they can be also custom dropdowns
        
        **Selection elements - choose correct action:**
        - `select` → ONLY for `<select>` dropdowns
        - `click` → For radio buttons, custom dropdowns, toggle buttons  
        - `check`/`uncheck` → For checkboxes

        **Key Rules:**
        - Prefer CSS selectors with attributes (name, id, data-*, type)
        - Use unique identifiers when available
        -- Keep selectors simple and robust
         
             
        **CRITICAL - AVOID GENERIC CLASS SELECTORS (especially for dropdowns/inputs that repeat):**
        ❌ BAD: input.oxd-input.oxd-input--active (matches sidebar Search AND form fields!)
        ❌ BAD: //div[@class='dropdown'][1]//span (wrong index syntax - index applies to child, not result set)
        ✅ GOOD: form .form-row input (scoped to form)
        ✅ GOOD: input[placeholder='Event Name'] (unique attribute)
        ✅ GOOD: //label[contains(text(),'Event')]/following::div[contains(@class,'select-text')][1] (XPath with label - BEST for multiple similar elements)
        ✅ GOOD: (//div[@class='dropdown']//span)[1] (correct index syntax - parentheses first, then index)
        
        === END SELECTOR GUIDELINES ===
        
        === FORM TARGETING ===
        - Look at the screenshot. ONLY target elements inside the MAIN FORM area.
        === END FORM TARGETING ===


        === YOUR TASK: FORM PAGE TESTING ===

        You are testing a FORM PAGE. The test flow is:
        You MUST generate steps to fill the form
        
        
        **Step 1: Fill the Form**
        
        **Form Structure:**
        - Input fields (text, email, number, date, etc.)
        - Selection controls (dropdowns, radio buttons, checkboxes)
        - Tabs or sections that organize the form
        - Navigation buttons (Next, Previous, Save, Submit)
        - List items (sections with "Add" / "Add New" / "+" buttons to add multiple entries)
        - File upload fields (input type="file")
        
        
        **⚠️ CRITICAL AND MANDATORY - DURING THE CREATION GIVE STEPS TO 100% OF ALL THE FIELDS - INCLUDING 100% OF ALL THE OPTIONAL ONES - MUST NOT SKIP ANY FIELD 
       
        ================================================================================
        
        - Fill ALL text inputs
        - Fill ALL textareas
        - Select options in ALL dropdowns
        - Check ALL checkboxes (if applicable)
        - Fill ALL date/time fields
        - Upload files to ALL file upload fields
        - Fill ALL fields in ALL tabs/sections
        - Fill ALL fields in modals/popups
        - Fill ALL fields in iframes
        - FILL ALL THE OPTIONAL FIELDS - DONT SKIP ANY
        
        **DO NOT skip fields just because they don't have a * (required) marker!**
        Real users fill all visible fields, not just required ones.
        ================================================================================
        
        **MANDATORY: LIST ITEMS HANDLING**
        ================================================================================
        If the form has sections for adding list items (e.g., "Add Finding", "Add Engagement", "+ Add Document"):
        
        **YOU MUST ADD EXACTLY 1 ITEM OF EACH TYPE** by following this pattern:
        
        **For Each List Item Type:**
        1. Click the "Add" / "Add New" / "+" button to open the item form/modal
        2. Fill ALL fields that appear in the modal/form
        3. Click the save/submit button ("Save", "Submit", "OK", "Add", "Accept", etc.)
        4. Wait for the modal to close or item to be added
        
        **If there are multiple different types of list items, add ONE of each type:**
        - If you see "Add Finding" → add 1 finding
        - If you see "Add Engagement" → add 1 engagement
        - If you see "Add Document" → add 1 document
        - etc.
        
        **Example Step Sequence (multiple types):**
        ```
        Step X: Click "Add Finding" button
        Step X+1: Fill "Finding Title" field
        Step X+2: Fill "Finding Description" field
        Step X+3: Click "Save" button
        Step X+4: Wait for modal to close (1 second)
        Step X+5: Click "Add Engagement" button
        Step X+6: Fill "Engagement Name" field
        Step X+7: Fill "Engagement Details" field
        Step X+8: Click "Save" button
        Step X+9: Wait for modal to close (1 second)
        ```
        
        **IMPORTANT:** Do not skip list items! If you see an "Add" button for a list, you MUST add 1 item of that type before moving to the next section.
        ================================================================================
        
        **MANDATORY: FILE UPLOAD HANDLING**
        ================================================================================
        **CRITICAL: If you see ANY file upload fields (`<input type="file">`), you MUST create and upload a file.**
        
        **File upload fields look like:**
        - `<input type="file" name="profileImage">`
        - `<input type="file" accept="image/*">`
        - `<input type="file" accept=".pdf,.doc">`
        - Label text like: "Upload Document", "Choose File", "Attach Resume", "Profile Picture"
        
        **For EVERY file upload field found, generate TWO sequential steps:**
        
        **Step 1: create_file** - Create appropriate test file based on the field's purpose
        **Step 2: upload_file** - Upload the created file
        
        **File Type Selection Guide:**
        - Resume/CV fields → create PDF with resume content
        - Profile/Photo/Image fields → create PNG or JPG image
        - Document/Report fields → create PDF or DOCX
        - Invoice/Receipt fields → create PDF with invoice data
        - Data/Spreadsheet fields → create CSV or XLSX
        - Generic "file" upload → create PDF
        
        **force_regenerate field (REQUIRED):**
        - Set to `true` for navigation actions: Edit, View, Next, Continue, Delete, Back to List buttons
        
        **Mandatory-dont_regenerate field:**
        - Set to `true` ONLY for:
          * Filling a field (fill action)
          * Opening/closing modals or dialogs
          * Adding/removing items in a list or table
          * Expanding/collapsing accordion sections
        - Set to `false` (or omit) for all other actions
        
        ** CRITICAL AND MANDATORY - force_regenerate field (for Save/Submit only):**
        - Set to `true` for Save and Submit buttons
        
        **full_xpath field (MANDATORY FOR ALL STEPS):**
        - Fallback selector if primary selector fails
        - Must start from `/html/body/...`
        - **COUNTING IS CRITICAL:** Count ALL direct children of each parent, including hidden elements, modals, overlays
        - Double-check your count
        - **USE IDs WHEN AVAILABLE:** If any element in the path has an ID, use it instead of counting:
          - ✅ `/html/body/div[@id='findingModal']/div/div[4]/button[2]`
          - ❌ `/html/body/div[3]/div/div[4]/button[2]` (counting is error-prone)
        - Only use indices `[n]` when no ID exists on that element
        - Trace the path carefully from body → target element using the DOM
        
        **⚠️ SELF-VERIFICATION (MANDATORY BEFORE RETURNING):**
        For EACH full_xpath you generate, you MUST verify it by tracing through the DOM:
        
        1. Start at `<body>` in the DOM
        2. For each segment in your path (e.g., `/div[2]`):
           - Find that element in DOM
           - Confirm tag name matches
           - Confirm index is correct (count ALL children of same tag, including hidden)
           - If using `[@id='x']` or `[@class='x']`, confirm attribute exists and matches
        3. Verify final element is your actual target
        
        **Example verification:**
        Your xpath: `/html/body/div[2]/form/div[3]/input[1]`
        
        CHECK:
        - body → has children: div#app, div#modal, script → div[2] = div#modal ✓ or ✗?
        - div#modal → has children: div.header, form → form = form ✓
        - form → has children: div, div, div, button → div[3] = third div ✓
        - div[3] → has children: label, input, span → input[1] = first input ✓
        
        If ANY check fails → FIX the xpath before returning.
        
        **Example 1: Resume Upload**
        ```json
        {{
          "step_number": 15,
          "action": "create_file",
          "file_type": "pdf",
          "filename": "test_resume.pdf",
          "content": "John Doe\\nSoftware Engineer\\n5 years experience\\nPython, Selenium, Testing",
          "selector": "",
          "value": "",
          "description": "Create test resume PDF",
          "full_xpath": "/html/body/.../element",
          "force_regenerate": false
        }},
        {{
          "step_number": 16,
          "action": "upload_file",
          "selector": "input[name='resumeUpload']",
          "value": "test_resume.pdf",
          "description": "Upload resume file",
          "full_xpath": "/html/body/.../element",
          "force_regenerate": false
        }}
        ```
        
        **Example 2: Profile Image Upload**
        ```json
        {{
          "step_number": 8,
          "action": "create_file",
          "file_type": "png",
          "filename": "profile_photo.png",
          "content": "Test Profile Photo\\nJohn Doe\\nID: 12345",
          "selector": "",
          "value": "",
          "description": "Create test profile image",
          "full_xpath": "/html/body/.../element",
          "force_regenerate": false
        }},
        {{
          "step_number": 9,
          "action": "upload_file",
          "selector": "input[type='file'][name='profileImage']",
          "value": "profile_photo.png",
          "description": "Upload profile photo",
          "full_xpath": "/html/body/.../element",
          "force_regenerate": false
        }}
        ```
        
        **Example 3: Document Upload**
        ```json
        {{
          "step_number": 22,
          "action": "create_file",
          "file_type": "pdf",
          "filename": "test_document.pdf",
          "content": "Test Document\\nDate: 2024\\nReference: TEST-001\\nApproved by QA Team",
          "selector": "",
          "value": "",
          "description": "Create test document PDF",
          "full_xpath": "/html/body/.../element",
          "force_regenerate": false
        }},
        {{
          "step_number": 23,
          "action": "upload_file",
          "selector": "input#documentUpload",
          "value": "test_document.pdf",
          "description": "Upload test document",
          "full_xpath": "/html/body/.../element",
          "force_regenerate": false
        }}
        ```
        
                        

        **IMPORTANT Rules:**
        - ALWAYS create files with simple, relevant content (3-5 lines)
        - Use descriptive filenames that match the field purpose
        - The filename in create_file MUST match the value in upload_file
        - File content should be contextual (resume for resume field, invoice for invoice field, etc.)
        - Never skip file upload fields - treat them as MANDATORY
        - Do NOT skip fields because they appear optional - fill EVERY visible field
        ================================================================================
        
        **CRITICAL: Tab/Section Handling:**
        If the form has tabs or sections:
        1. Click the FIRST tab
        2. Fill ALL visible fields in that tab completely
        3. Click the SECOND tab
        4. Fill ALL visible fields in that tab completely
        5. Repeat for EVERY tab/section
        6. Only after ALL tabs are filled → click Next or Submit
        
        **CRITICAL: Fill fields in the order a user would encounter them.**
        - If a field is inside a tab, you MUST click that tab FIRST before filling its fields
        - Do NOT try to fill fields from tabs that aren't active yet
        - Only generate fill steps for fields you can actually SEE in the current DOM
        - Use the EXACT selectors from the DOM (id, name, class attributes)
        - Do NOT guess field names or make up selectors that don't exist in the DOM
        
        **DO NOT skip tabs! Every tab must be filled before moving forward!**
        
        **Forms with Multiple Save Sections:**
        Some forms have independent sections, each with its own Save button (not one final Submit).
        If you see multiple Save buttons within the form (e.g., "Save Personal Info", "Save Address", "Save Employment"):
        1. Fill all fields in Section 1
        2. Click Section 1's Save button
        3. Wait for save confirmation (if any)
        4. Fill all fields in Section 2
        5. Click Section 2's Save button
        6. Continue for each section
        
        **How to identify:** Look for Save/Update buttons that appear WITHIN form sections, not just at the bottom.
        **Do NOT set force_regenerate_verify: true for section saves** — only for the FINAL form submission (if any).
        
        **Junctions:** Mark a step as a junction if ANY of these are true:
        - The element is one of several options the user can choose from (radio buttons, option cards, dropdown, toggle buttons, etc.)
        - Selecting it MIGHT reveal/show different fields than selecting a sibling option
        - The element looks like a choice/option/selection among alternatives
        
        **When in doubt, mark it as a junction** - we verify junctions automatically, so false positives are OK but missing a junction is bad.

        **Junction types:** dropdowns, radio buttons, checkboxes, toggle buttons, option cards, segmented controls, or any element where you choose ONE option from several alternatives.

        **CRITICAL - ALWAYS MARK AS JUNCTION:**
        - If you are clicking ONE of SEVERAL similar elements (e.g., one radio button among many, one card among several cards, one option among choices) → it IS a junction
        - If the element is part of a group where user must choose ONE and the choice affects which fields appear (radio group, option cards) → it IS a junction
        - If clicking this element could potentially show different fields than clicking its sibling elements → it IS a junction

        **IMPORTANT:** When clicking any element that LOOKS LIKE it could show/hide different panels or field sets (e.g., it's one of several similar options, it's a radio button, it's an option card), mark it as a junction. Use the selector of the element you actually click for the action, and use the most relevant `name` or `id` attribute for `junction_name`.
        
        **Junction format:**
        ```json
        {{"action": "select", "selector": "...", "value": "...", "is_junction": true, "junction_info": {{"junction_name": "fieldName", "all_options": ["option1", "option2"], "chosen_option": "option1"}}, "description": "...", "full_xpath": "/html/body/.../element", "force_regenerate": false}}
        ```
        
        **junction_info fields (ALL REQUIRED):**
        - `junction_name`: Use element's `name` or `id` attribute
        - `all_options`: List ALL available options from DOM - for `<select>` dropdowns, ONLY include values from actual `<option>` tags inside the `<select>`. Do NOT infer options from HTML comments, CSS classes, or JavaScript code.
        - `chosen_option`: The option you are selecting
        
        Always include `is_junction: true` and `junction_info` even when following junction instructions.
        
        
        **Your Testing Path - Act Like a Real User:**
        You should follow ONE RANDOM path through the form, like a real user would:
                        
        Don't generate just the click and stop! Generate the complete flow!
        
        1. Start at the beginning of the form
        2. If form has tabs, process them ONE BY ONE:
           - Click Tab 1 → Fill ALL fields in Tab 1
           - Click Tab 2 → Fill ALL fields in Tab 2
           - Click Tab 3 → Fill ALL fields in Tab 3
           - etc.
        3. Fill ALL visible fields in the order they appear (not just required ones)
        4. At each junction (dropdown, radio button, checkbox), check test_data for specified values first, otherwise make a RANDOM selection
        5. After selecting, fill ANY new fields that appear
        6. Continue filling all visible fields in order
        7. Handle special elements:
           - Star ratings → Click on stars
           - Fields behind barriers (iframe, shadow DOM) → Use available tools to access them
           - Checkboxes → Check them if needed
           - Hidden fields revealed by hover/click → Fill them
        8. After ALL sections/tabs are complete → click Next or Submit
        9. Continue through multi-step forms
        10. Eventually reach and click the final Save/Submit button
        11. After submission/save, if there are more test cases (TEST_2, TEST_3, etc.), continue generating steps for them - do NOT stop at TEST_1

        **CRITICAL: Access ALL Fields:**
        Your goal is to fill EVERY visible field, regardless of where it is.
        If fields require special access (inside iframe, shadow DOM, nested structures), 
        use the available tools (switch_to_frame, switch_to_shadow_root, etc.) to reach them.
        Generate whatever steps are necessary to access and fill ALL fields.

        **CRITICAL Rules for Real User Behavior:**
        - Fill fields in the ORDER a user would encounter them (top to bottom, if inside a tab then click tab first)
        - Only generate fill steps for fields that ACTUALLY EXIST in the DOM with real selectors
        - Do NOT guess or hallucinate field names - read them from the DOM attributes (name, id, class)
        - Fill ALL visible fields (required AND optional) - users often fill everything
        - Process EVERY tab/section before clicking Next
        - Check test_data for field values first, make RANDOM selections only when not specified in test_data (don't always pick the first option)
        - After each junction choice, check for newly visible fields and fill them ALL
        - Handle iframes, star ratings, and special UI elements
        - Continue until you find Next/Continue button or Save/Submit button
        - Follow this single random path to completion

        === TEST CONTEXT & CREDENTIALS ===


        **Form Data Guidelines:**
        When generating test data for forms:
        
        **⚠️ DATE FIELDS - CRITICAL:** For date fields with "mm/dd/yyyy" placeholder → enter digits only: "01152025" (no slashes)
        
        **⚠️ ONLY THE MAIN/PRIMARY FIELD NEEDS UNIQUE SUFFIX:** 
        - ONLY the main identifying field (e.g., Person Name, Company Name, Title) gets prefix "quattera_" + name + random suffix of 5 TRULY RANDOM digits
        - Generate NEW random digits each time - do NOT reuse digits like 12345, 84729, or 00000
        - ALL OTHER FIELDS should have NORMAL realistic values WITHOUT any suffix!
        
        - Name (main field): {'Add quattera_ prefix + unique suffix (e.g., quattera_TestUser_184093)'}
        - Email: {'Normal email like john@example.com (NO suffix!)'}
        - Phone, Address, City, State, Zip, Country, Numbers: Normal realistic values (NO suffix!)
        - Dates: Look at screenshot/placeholder for required format
        - **EXCEPTION for fill_autocomplete:** Even for main/leading fields, use ONLY "quattera" - the full value with suffix will be selected from the dropdown suggestions in the next step
        
        **⚠️ SPECIAL INPUT FIELDS (Date, Time, Phone, etc.) - CRITICAL:**
        For date, time, and specially formatted fields:
        1. Look at the SCREENSHOT to see the field's placeholder/format hint
        2. Enter the value in the EXACT format shown in the placeholder
        3. For date fields with "mm/dd/yyyy" placeholder → enter digits only: "01152025" (no slashes)
        4. The placeholder tells you how to format your input - follow it exactly!
        
        **Wrong format will corrupt the data and cause verification failures!**


        === AVAILABLE ACTIONS ===

        **Standard Actions:**
        - click: Click element (buttons, links, tabs)
        - double_click: Double-click element (some elements require it)
        - fill: Enter text in input field (use ONLY for regular text inputs WITHOUT autocomplete/suggestions)
        - fill_autocomplete: Type "quattera" in autocomplete field to trigger suggestions. The actual value is selected in the next step by clicking on suggestion. MUST always have force_regenerate: true
        - NOTE: fill action automatically clears field first - NO separate clear step needed
        - select: Choose from dropdown OR select radio button
        - check: Check checkbox (only if not already checked)
        - uncheck: Uncheck checkbox (only if currently checked)
        - drag_and_drop: Drag element to target (selector: source, value: target selector)
        - press_key: Send keyboard key (value: ENTER, TAB, ESCAPE, ARROW_DOWN, etc.)
        - slider: Set single-handle slider. Provide ONLY the rail/track selector.
        - range_slider: Set two-handle range slider. Provide ONLY the rail/track selector.
        - wait_for_visible: Wait for element to become visible
        - wait: Wait for duration (MAX 10 seconds!) OR wait for element to be ready if selector provided
        - wait_for_ready: Wait for AJAX-loaded element to become interactable (use for dynamic fields)
        - wait_for_visible: Wait for element to become visible (max 10s)
        - wait_for_hidden: Wait for element to disappear (max 10s, useful for loading spinners)
        - scroll: Scroll to element
        - refresh: Refresh the page

        **Special Access Tools (use when needed to reach fields):**
        - switch_to_frame: Access fields inside iframe
        - switch_to_parent_frame: Navigate back one iframe level
        - switch_to_default: Return to main page context
        - switch_to_shadow_root: Access fields inside shadow DOM
        - switch_to_window: Switch to window/tab by index (value: 0, 1, 2, etc.)
        - switch_to_parent_window: Return to original/main window
        
        
        
        **DRAG AND DROP ACTION:**
        For drag-and-drop elements (like project priority assignment):
        ```json
        {{"action": "drag_and_drop", "selector": ".project-item#projectAlpha", "value": ".priority-box.high-priority", "description": "Drag Project Alpha to High Priority box"}}
        ```
        Selector = element to drag, value = target drop zone selector.
        
        **PRESS KEY ACTION:**
        Send keyboard keys to elements or active element:
        ```json
        {{"action": "press_key", "selector": "input#search", "value": "ENTER", "description": "Press Enter in search field"}}
        ```
        Available keys: ENTER, TAB, ESCAPE, SPACE, BACKSPACE, DELETE, ARROW_UP, ARROW_DOWN, ARROW_LEFT, ARROW_RIGHT, HOME, END, PAGE_UP, PAGE_DOWN
        
        **SLIDER ACTIONS:**
        For sliders, provide only the rail/track selector - agent handles clicking and reading values:
        ```json
        {{"action": "slider", "selector": "input[type='range']#volume", "description": "Set volume slider"}}
        {{"action": "range_slider", "selector": ".price-range-track", "description": "Set price range filter"}}
        ```
        **CHECKBOX ACTIONS:**
        Use `check` and `uncheck` for explicit checkbox control (better than click):
        ```json
        {{"action": "check", "selector": "input#agreeToTerms", "description": "Check terms agreement checkbox"}}
        {{"action": "uncheck", "selector": "input#newsletter", "description": "Uncheck newsletter subscription"}}
        ```
        
        **WINDOW/TAB SWITCHING:**
        When a new window/tab opens:
        ```json
        {{"action": "switch_to_window", "value": "1", "description": "Switch to newly opened window"}}
        ... do actions in new window ...
        {{"action": "switch_to_parent_window", "description": "Return to original window"}}
        ```

        **CRITICAL WAIT RULES:**
        - **NEVER use wait with value > 10 seconds!** (will cause timeout)
        - For time-based wait: {{"action": "wait", "value": "2"}} (max 10 seconds)
        - For AJAX/dynamic fields: {{"action": "wait_for_ready", "selector": "#dependentField"}}
        - For visibility: {{"action": "wait_for_visible", "selector": "#loadedContent"}}
        - For disappearing elements: {{"action": "wait_for_hidden", "selector": ".loading-spinner"}}
        - wait_for_ready waits up to 10s for element to be clickable/enabled
        - **For wait actions, keep selectors simple** - use IDs, classes, or basic attributes. Avoid complex CSS like :not(), :has(), or pseudo-selectors that may not work reliably with Selenium's wait conditions.

        **AJAX/Dynamic Field Handling:**
        When a field loads via AJAX (e.g., Field B appears after filling Field A):
        ```json
        {{"action": "fill", "selector": "input#fieldA", "value": "SomeValue", "field_name": "Field A"}},
        {{"action": "wait_for_ready", "selector": "input#fieldB", "description": "Wait for Field B to load via AJAX"}},
        {{"action": "fill", "selector": "input#fieldB", "value": "AnotherValue", "field_name": "Field B"}}
        ```

        **IMPORTANT: Use 'select' action for BOTH:**
        - <select> dropdowns: {{"action": "select", "selector": "select[name='country']", "value": "USA"}}
        - Radio buttons: {{"action": "select", "selector": "input[value='option1']", "value": "option1"}}
        
        === DISCOVERY FIELDS (force_regenerate) ===

        When generating a step, ask yourself:
        "Can I see in the DOM what I need to interact with AFTER this action?"

        - YES → Complete normally
        - NO → MANDATORY - Use force_regenerate: true, you'll be called again with updated DOM

        **The Pattern:**
        1. Trigger action (click/fill) + force_regenerate: true
        2. System executes, waits for DOM to stabilize, re-extracts DOM
        3. You're called again with updated DOM showing the revealed content
        4. Generate the next step(s) with now-visible elements

        **Common Discovery Scenarios:**
        - Custom dropdown: options hidden until clicked
        - Autocomplete: suggestions hidden until typing
        - Date picker: calendar hidden until focused
        - Any element that reveals hidden content on interaction

        **Custom Dropdown Example (Only if it is not a native select):**
        Step 1:
        {{"action": "click", "selector": ".dropdown-trigger", "field_name": "gender", "description": "Open dropdown", "force_regenerate": true}}

        Step 2 (after regeneration - options now visible):
        {{"action": "click", "selector": "//li[contains(text(), 'Option A')]", "field_name": "male", "description": "Select Option A"}}
        
        
        
        **Fill Autocomplete Example:**
        Step 1:
        {{"action": "fill_autocomplete", "selector": "input#city", "value": "quattera", "description": "Type to trigger suggestions", "force_regenerate": true}}

        Step 2 (after regeneration - suggestions now visible):
        {{"action": "click", "selector": "//ul[@class='suggestions']/li[1]", "field_name": "quattera_first", "description": "Select first suggestion"}}

        **⚠️ field_name (REQUIRED for ALL click and fill actions):**
        For ALL click and fill actions, ALWAYS include `field_name` with the EXACT label text:
        - `field_name` must match the field's label EXACTLY as shown on page (case-insensitive)
        - Used as fallback if selector fails
        - Example: If label shows "House Color", use `"field_name": "House Color"`
        ** Exception - for dropdown items the field_name is the dropdown specific item name
        
        **RULE:** If you cannot see in the DOM what you need to select/click after an action, use force_regenerate: true.

        === COMPLEX FIELDS (Atomic Step Sequences) ===

        Some fields require multiple atomic steps to complete.

        **RULE:**
        1. If the field matches a specific action type (select, slider, check, etc.) → use that action
        2. If the field does NOT match any specific action type → examine the DOM and generate a sequence of atomic actions (click, fill, press_key, etc.)

        **Examples:**
        - Multiple input boxes (OTP/PIN) → fill each box separately
        - Tag input requiring confirmation → fill + press_key ENTER

        Analyze the DOM, understand the field's structure, and generate appropriate atomic steps.
        
        === CURRENT PAGE DOM ===

        {dom_html}


        === TEST CASES TO IMPLEMENT ===

        **CRITICAL: You must execute ALL test cases listed below, one after another, in a single continuous flow.**
        
        - Complete TEST 1, then immediately continue to TEST 2, then TEST 3, etc.
        - Do NOT stop after completing one test - generate steps for ALL tests
        - All steps must be in ONE JSON array covering the complete flow
        
        **EXAMPLE FLOW:**
        - TEST_1 steps (fill and submit form) → form saves → page navigates to list
        - TEST_2 steps (verify form appears in list table) → verify the data in list
        - TEST_3 steps (click to view details) → verify all fields show correct values
        
        **After form submission in TEST_1, the page will navigate automatically. Continue generating steps for TEST_2 and TEST_3 on the new page!**

        {json.dumps(test_cases, indent=2)}

        **CRITICAL: Generate complete steps for current test case + 2-4 steps from next test case. This ensures execution continues after save/submit.**

        
        **For edit/update tests - COMPLETE WORKFLOW PER FIELD:**
        For each field that needs to be verified and updated, generate this complete sequence:
        
        1. **Navigate to the field** (if needed):
           - Switch to iframe: use switch_to_frame if field is in iframe
           - Switch to shadow DOM: use switch_to_shadow_root if field is in shadow root
           - Click tab: if field is in a different tab/section
           - Hover: if field is hidden and needs hover to reveal
           - Wait: use wait_for_visible if field loads dynamically
        
        
        
        2. **Fill automatically clears** - no separate clear step needed
        
        3. **Update the field** with new value:
           - Action: "fill" or "select" or "check" (depending on field type)
           - Selector: the field selector
           - Value: the new updated value
        
        4. **Navigate back** (if needed):
           - Switch back from iframe: use switch_to_default
           - Switch back from shadow DOM: use switch_to_default
        
        **Example for field in iframe:**
        - switch_to_frame (navigate to iframe)
        - fill (update with new value)
        - switch_to_default (exit iframe)
        
        **Example for field requiring hover:**
        - hover (reveal hidden field)
        - wait_for_visible (wait for field to appear)
        - fill (update with new value)

        === OUTPUT REQUIREMENTS ===

        1. **Return ONLY valid JSON array** - no explanations, no markdown, just JSON

        2. **Each action must have these fields:**
           - "step_number": integer (sequential, starting from 1)
           - "test_case": string (which test this belongs to)
           - "action": string (navigate, click, fill, select, etc.)
           - "description": string (human-readable description)
           - "selector": string or null (CSS selector is preferred - see guidelines above!)
           - "value": string or null (value for fill/select actions)
           - "verification": string or null (what to verify after action)
           - "wait_seconds": number (seconds to wait after action)
           - "is_junction": boolean (optional - for dropdowns/radios/checkbox groups)
           - "junction_info": object (optional - {{"all_options": [...], "chosen_option": "..."}})

        3. **Selector Selection Process (follow this order):**
           Step 1: Look for data-qa, data-testid, data-test attributes → USE THESE FIRST
           Step 2: Look for unique name, type, id attributes → USE THESE SECOND
           Step 3: Look for unique IDs (#something) → USE THESE THIRD
           Step 4: Look for specific classes with context (.form .submit-btn) → USE THESE FOURTH
           Step 5: Use structural selectors (form > button:last-child) → LAST RESORT

        **CRITICAL: Modal Button Selectors (Save/Submit/OK/Cancel):**
           Modal buttons require EXTRA PRECISION to avoid ambiguity. ALWAYS use XPath for modal buttons:
           
           **PREFERRED XPATH STRATEGIES (in order):**
           1. **XPath with onclick attribute** (BEST):
              `//button[@onclick='saveEngagement()']`
              `//div[@id='engagementModal']//button[@onclick='saveEngagement()']`
           
           2. **XPath scoped to specific modal + text content**:
              `//div[@id='engagementModal']//button[contains(text(), 'Save')]`
              `//div[contains(@class, 'modal') and contains(@style, 'display')]//button[contains(text(), 'Save')]`
           
           3. **XPath with modal scope + button attributes**:
              `//div[@id='findingModal']//button[@type='submit']`
              `//div[contains(@class, 'modal-dialog')]//button[contains(@class, 'btn-primary')]`
           
           **WHY XPath for modals:**
           - Multiple modals may exist in DOM with similar button classes
           - XPath can scope to the visible/active modal container
           - XPath can use text content for precision
           - CSS selectors like `.modal button.btn-save` may match multiple elements
           
           **EXAMPLES:**
           - ❌ BAD: `button.btn-save-engagement` (ambiguous, may match hidden modal)
           - ❌ BAD: `button.btn-primary` (too generic)
           - ✅ GOOD: `//button[@onclick='saveEngagement()']` (unique function name)
           - ✅ GOOD: `//div[@id='engagementModal']//button[contains(text(), 'Save')]` (scoped to modal)
           
           **For non-modal buttons, continue using CSS selectors as normal.**

        

        4. **Wait Times:**
           - After navigate: 2 seconds
           - After click (page change): 2 seconds
           - After fill: 0.5 seconds

        5. **Breaking Down Generic Steps:**
           - "Fill form fields" → Generate fill steps for EACH VISIBLE field (required AND optional)
           - "Complete form" → Generate steps for all sections/tabs
           - "Navigate to next section" → Click next button and verify new section
           - "Make random selection" → For dropdowns/radios, FIRST check if test_data specifies a value for this field (match by field name). If test_data has a value, use it exactly. If not specified in test_data, choose randomly from available options
           - **"Add list items" → Generate steps to add EXACTLY 1 ITEM OF EACH TYPE: If you see "Add Finding" → add 1 finding, if you see "Add Engagement" → add 1 engagement, etc.**
           - Real users fill ALL visible fields, not just required ones!


        === EXAMPLE OUTPUT ===

        [
          {{
            "step_number": 1,
            "test_case": "Complete Form Following Random Path",
            "action": "click",
            "description": "Click 'Add New' button to open form",
            "selector": "button.add-new",
            "field_name": "Add New",
            "value": null,
            "verification": "form opens",
            "wait_seconds": 2,
            "full_xpath": "/html/body/div[1]/main/button"
          }},
          {{
            "step_number": 2,
            "test_case": "Complete Form Following Random Path",
            "action": "fill",
            "description": "Enter name in form",
            "selector": "input[name='name']",
            "field_name": "Name",
            "value": "quattera_TestUser_184093",
            "verification": null,
            "wait_seconds": 0.5,
            "full_xpath": "/html/body/div[1]/form/input[1]"
          }},
          {{
            "step_number": 3,
            "test_case": "Complete Form Following Random Path",
            "action": "click",
            "description": "Click address tab",
            "selector": "button[data-tab='address']",
            "field_name": "Address",
            "value": null,
            "verification": null,
            "wait_seconds": 1,
            "full_xpath": "/html/body/div[1]/form/div[2]/button[3]"
          }},
          {{
            "step_number": 4,
            "test_case": "Complete Form Following Random Path",
            "action": "switch_to_frame",
            "description": "Access address iframe",
            "selector": "iframe#address-frame",
            "value": null,
            "verification": null,
            "wait_seconds": 1,
            "full_xpath": "/html/body/div[1]/form/iframe"
          }},
          {{
            "step_number": 5,
            "test_case": "Complete Form Following Random Path",
            "action": "fill",
            "description": "Fill street address",
            "selector": "input[name='street']",
            "field_name": "Street Address",
            "value": "123 Main St",
            "verification": null,
            "wait_seconds": 0.5,
            "full_xpath": "/html/body/form/input[1]"
          }},
          {{
            "step_number": 6,
            "test_case": "Complete Form Following Random Path",
            "action": "switch_to_default",
            "description": "Return to main page",
            "selector": null,
            "value": null,
            "verification": null,
            "wait_seconds": 0.5,
            "full_xpath": ""
          }},
          {{
            "step_number": 7,
            "test_case": "Complete Form Following Random Path",
            "action": "fill",
            "description": "Fill Field A (triggers AJAX)",
            "selector": "input#fieldA",
            "field_name": "Field A",
            "value": "SampleValue",
            "verification": null,
            "wait_seconds": 0.5,
            "full_xpath": "/html/body/div[1]/form/input[@id='fieldA']"
          }},
          {{
            "step_number": 8,
            "test_case": "Complete Form Following Random Path",
            "action": "wait_for_ready",
            "description": "Wait for Field B to load via AJAX",
            "selector": "input#fieldB",
            
            "value": null,
            "verification": null,
            "wait_seconds": 0,
            "full_xpath": "/html/body/div[1]/form/input[@id='fieldB']"
          }},
          {{
            "step_number": 9,
            "test_case": "Complete Form Following Random Path",
            "action": "fill",
            "description": "Fill Field B",
            "selector": "input#fieldB",
            "field_name": "Field B",
            "value": "DependentValue",
            "verification": null,
            "wait_seconds": 0.5,
            "full_xpath": "/html/body/div[1]/form/input[@id='fieldB']"
          }},
          {{
            "step_number": 9,
            "test_case": "Complete Form Following Random Path",
            "action": "click",
            "description": "Click the Add button to add a new finding item",
            "selector": "button.btn-add-finding",
            "field_name": "Add",
            "value": null,
            "verification": null,
            "wait_seconds": 0.5,
            "full_xpath": "/html/body/div[1]/form/div[3]/button"
          }},
          {{
            "step_number": 10,
            "test_case": "Complete Form Following Random Path",
            "action": "select",
            "description": "Select inquiry type (random choice)",
            "selector": "select[name='inquiry_type']",
            "value": "General",
            "verification": null,
            "wait_seconds": 0.5,
            "full_xpath": "/html/body/div[1]/form/select"
          }},
          {{
            "step_number": 8,
            "test_case": "Complete Form Following Random Path",
            "action": "click",
            "description": "Click submit button",
            "selector": "button[type='submit']",
            "field_name": "Submit",
            "value": null,
            "verification": "form submitted",
            "wait_seconds": 2,
            "full_xpath": "/html/body/div[1]/form/button[@type='submit']"
          }},
          {{
            "step_number": 9,
            "test_case": "Complete Form Following Random Path",
            "action": "wait_for_hidden",
            "description": "Wait for success message to disappear",
            "selector": ".success-message",
            "value": null,
            "verification": "success message disappeared",
            "wait_seconds": 1,
            "full_xpath": "/html/body/div[2]/div"
          }}
        ]


        === FINAL CHECKLIST BEFORE RESPONDING ===

        Before you output your JSON, verify:
        ☐ NO :has-text() selectors anywhere
        ☐ NO :contains() selectors anywhere  
        ☐ NO :text() selectors anywhere
        ☐ ALL selectors use attributes, IDs, classes, or structure
        ☐ Each generic step expanded into specific actions
        ☐ Following ONE path through the form
        ☐ Valid JSON format (no trailing commas, proper quotes)

        === RESPONSE FORMAT ===
        Return ONLY a JSON object with this structure:
        ```json
        {{
          "steps": [
            {{"step_number": 1, "action": "fill", "selector": "input#field", "value": "value", "field_name": "Field", "description": "Fill field", "full_xpath": "/html/body/div[1]/form/input", "force_regenerate": false, "dont_regenerate": false}},
            {{"step_number": 2, "action": "click", "selector": "button.submit", "field_name": "Submit", "description": "Submit form", "full_xpath": "/html/body/div[1]/form/button", "force_regenerate": true, "dont_regenerate": false}}
          ]
        }}
        ```
                        
        **force_regenerate field (REQUIRED):**
        - Set to `true` for navigation actions: Edit, View, Next, Continue, Delete, Back to List buttons
        - Set to `false` for: fill, select, click tab, check, hover, verify, scroll, ALL wait actions, switch_to_frame, switch_to_default
        
        **MANDATORY-dont_regenerate field:**
        - Set to `true` ONLY for:
          * Filling a field (fill action)
          * Opening/closing modals or dialogs
          * Adding/removing items in a list or table
          * Expanding/collapsing accordion sections
        - Set to `false` (or omit) for all other actions
        
        - This tells the system to regenerate steps after this action completes

        - **steps**: Array of step objects to execute

        Return ONLY the JSON object, no other text.
        """
        
        try:
            logger.info("[AIHelper] Sending request to Claude API...")
            print("[AIHelper] Sending request to Claude API...")

            # Use retry wrapper (with or without screenshot)
            if screenshot_base64:
                # Use multimodal API with screenshot
                message_content = [
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
                #print("\n" + "!" * 80)
                #print("!!!!!!!!!!!!! GENERATE_TEST_STEPS - (WITH IMAGE) FINAL PROMPT TO AI !!!!")
                #print("!" * 80)
                #import re
                #prompt_no_dom = re.sub(r'## Current Page DOM:.*?(?=\n[A-Z=\*#])', '## Current Page DOM:\n[DOM REMOVED FOR LOGGING]\n\n', prompt, flags=re.DOTALL)
                #print(prompt_no_dom)
                #print("!" * 80 + "\n")
                print("!*!*!*!*!*!*!*! Entering the AI func for generate steps")
                # Debug mode: log full prompt
                if self.session_logger and self.session_logger.debug_mode:
                    import re
                    prompt_for_log = re.sub(r'## Current Page DOM:.*?(?=\n[A-Z#=\*]|$)',
                                            '## Current Page DOM:\n[DOM TRUNCATED FOR LOG]\n\n', prompt,
                                            flags=re.DOTALL)
                    self.session_logger.ai_call("generate_steps", prompt_size=len(prompt), prompt=prompt_for_log)
                response_text = self._call_api_with_retry_multimodal(message_content, max_tokens=16000, max_retries=3)
            else:
                # Text-only API (backward compatibility)
                #print("\n" + "!" * 80)
                #print("!!!!!!!!!!!!!!! GENERATE_TEST_STEPS - (NO IMAGE ..??) FINAL PROMPT TO AI !!!!")
                #print("!" * 80)
                #import re
                #prompt_no_dom = re.sub(r'## Current Page DOM:.*?(?=\n[A-Z=\*#])', '## Current Page DOM:\n[DOM REMOVED FOR LOGGING]\n\n', prompt, flags=re.DOTALL)
                #print(prompt_no_dom)
                #print("!" * 80 + "\n")
                response_text = self._call_api_with_retry(prompt, max_tokens=16000, max_retries=3)



            if response_text is None:
                print("[AIHelper] ❌ Failed to get response from API after retries")
                logger.error("[AIHelper] Failed to get response from API after retries")
                return {"steps": [], "ui_issue": "", "no_more_paths": False}

            logger.info(f"[AIHelper] Received response ({len(response_text)} chars)")
            print(f"[AIHelper] Received response ({len(response_text)} chars)")
            # Debug mode: log full response
            if self.session_logger and self.session_logger.debug_mode:
                self.session_logger.ai_response("generate_steps", success=True, response=response_text)
            
            # Parse JSON from response
            response_text = response_text.strip()
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.startswith("```"):
                response_text = response_text[3:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            response_text = response_text.strip()
            
            # Try parsing as object first (new format)
            try:
                result = json.loads(response_text)
                if isinstance(result, dict) and "steps" in result:
                    # New format: {"steps": [...], "no_more_paths": bool}
                    steps = result.get("steps", [])

                    logger.info(f"[AIHelper] Successfully parsed {len(steps)} steps")
                    print(f"[AIHelper] Successfully parsed {len(steps)} steps")

                    # DEBUG: Print full response when 0 steps returned
                    if len(steps) == 0:
                        print("=" * 80)
                        print("[AIHelper] ⚠️ DEBUG: GENERATE STEPS RETURNED 0 STEPS")
                        print("=" * 80)
                        print(f"[AIHelper] Full AI response:\n{response_text}")
                        print("=" * 80)

                    # Check if AI detected validation errors
                    if result.get("validation_errors_detected"):
                        print(f"[AIHelper] ⚠️ !!!!!!! Validation errors detected in DOM/screenshot")
                        print(response_text)
                        return {
                            "steps": [],
                            "validation_errors_detected": True,
                            "ui_issue": "",
                            "no_more_paths": False
                        }

                    # Check if AI detected page errors
                    if result.get("page_error_detected"):
                        print(f"[AIHelper] ⚠️ !!!!!!! Page error detected in DOM/screenshot")
                        return {
                            "steps": [],
                            "page_error_detected": True,
                            "error_type": result.get("error_type", "unknown"),
                            "ui_issue": "",
                            "no_more_paths": False
                        }

                    
                    return {"steps": steps, "ui_issue": "", "no_more_paths": False}
                elif isinstance(result, list):
                    # Old format: just array of steps (backward compatibility)
                    logger.info(f"[AIHelper] Successfully parsed {len(result)} steps (legacy format)")
                    print(f"[AIHelper] Successfully parsed {len(result)} steps (legacy format)")
                    return {"steps": result, "ui_issue": "", "no_more_paths": False}
                else:
                    raise ValueError("Unexpected response format")
            except (json.JSONDecodeError, ValueError) as e:
                # Failed to parse
                result_logger_gui.error(f"[AIHelper] Failed to parse JSON: {e}")
                print(f"[AIHelper] Failed to parse JSON: {e}")
                print(f"[AIHelper] Raw response:\n{response_text}")
                raise AIParseError(f"JSON parse error: {e}")

        except AIParseError:
            raise

        except Exception as e:
            result_logger_gui.error(f"[AIHelper] Error: {e}")
            print(f"[AIHelper] Error: {e}")
            import traceback
            traceback.print_exc()
            raise AIParseError(f"Unexpected error: {e}")

    def regenerate_steps(
            self,
            dom_html: str,
            executed_steps: list,
            test_cases: list,
            test_context,
            screenshot_base64: Optional[str] = None,
            critical_fields_checklist: Optional[Dict[str, str]] = None,
            field_requirements: Optional[str] = None,
            junction_instructions: Optional[str] = None,
            user_provided_inputs: Optional[Dict] = None,
            retry_message: Optional[str] = None,
            mapping_hints: str = ""
    ) -> Dict[str, Any]:
        """
        Regenerate remaining steps after DOM change

        Args:
            dom_html: Current page DOM (after change)
            executed_steps: Steps already executed
            test_cases: Test cases
            test_context: Test context
            screenshot_base64: Optional base64 screenshot for visual context

        Returns:
            Dict with 'steps' (list), 'ui_issue' (string), and 'no_more_paths' (bool)
        """

        if self.session_logger:
            self.session_logger.info("🤖 !*!*!* Entering FORM MAPPER prompter: regenerate_steps", category="ai_routing")

        try:
            print(f"[AIHelper] Regenerating steps after DOM change...")
            print(f"[AIHelper] Already executed: {len(executed_steps)} steps")

            ##   DEBUG ###
            '''
            if screenshot_base64:
                try:
                    import base64 as b64_module
                    import os
                    from datetime import datetime
                    screenshots_dir = "/tmp/debug_screenshots"
                    os.makedirs(screenshots_dir, exist_ok=True)
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                    screenshot_path = os.path.join(screenshots_dir, f"{timestamp}_into_ai_regenerate.png")
                    with open(screenshot_path, 'wb') as f:
                        f.write(b64_module.b64decode(screenshot_base64))
                    print(f"\n{'!' * 80}\n!!! SCREENSHOT SAVED: {screenshot_path}\n{'!' * 80}\n")
                except Exception as e:
                    print(f"[AIHelper] Warning: Failed to save debug screenshot: {e}")
            '''
            ### END DEBUG ####

            # Build context of what's been done
            executed_context = ""
            if executed_steps:
                executed_context = f"""
## Steps Already Completed:
{json.dumps([{"step": i + 1, "action": s.get("action"), "description": s.get("description"), "selector": s.get("selector"), "value": s.get("value"), "force_regenerate": s.get("force_regenerate", False)} for i, s in enumerate(executed_steps)], indent=2)}
"""

            # Build test cases context
            test_cases_context = ""
            if test_cases:
                test_cases_context = f"""
## Test Cases:
{json.dumps(test_cases, indent=2)}
"""

            # Build critical fields checklist section (for Scenario B recovery)
            critical_fields_section = ""
            if critical_fields_checklist:
                fields_list = "\n".join([f"- **{field_name}**: {issue_type}" for field_name, issue_type in
                                         critical_fields_checklist.items()])
                requirements_text = f"\n**EXACT REQUIREMENTS FROM ALERT:**\n{field_requirements}\n" if field_requirements else ""

                critical_fields_section = f"""
⚠️ ALERT RECOVERY MODE ⚠️
The following fields MUST be filled correctly:
{fields_list}
{requirements_text}
These fields caused the previous failure - pay special attention to them.

"""

            # Junction instructions for multi-path discovery
            route_planning_section = ""
            if junction_instructions:
                route_planning_section = f"""
🔀 REQUIRED SELECTIONS FOR THIS PATH:
{junction_instructions}

For dropdowns or selection fields listed above, you MUST select the specified option.
For ALL OTHER fields (including dropdowns/selections NOT listed above), you MUST still fill/select them - just choose any valid option.
Do NOT skip fields just because they are not in the required selections list.
"""

            # User-provided inputs section
            user_inputs_section = ""
            # Check for test scenario content (raw text)
            if user_provided_inputs and user_provided_inputs.get("content") and user_provided_inputs.get(
                    "source") == "test_scenario":
                scenario_name = user_provided_inputs.get("scenario_name", "Test Scenario")
                content = user_provided_inputs.get("content", "")
                user_inputs_section = f"""
{'=' * 60}
Use these field values when filling matching fields:

{content}

{'=' * 60}
"""
            elif user_provided_inputs and (
                    user_provided_inputs.get("field_values") or user_provided_inputs.get("file_paths")):
                field_values = user_provided_inputs.get("field_values", [])
                file_paths = user_provided_inputs.get("file_paths", [])

                lines = ["📋 USER-PROVIDED INPUTS (MANDATORY)", "=" * 60,
                         "Use these EXACT values when filling matching fields:", ""]

                if field_values:
                    lines.append("FIELD VALUES:")
                    for fv in field_values:
                        lines.append(f"- {fv.get('field_hint', 'unknown')} → {fv.get('value', '')}")
                    lines.append("")

                if file_paths:
                    lines.append("FILE PATHS (use for file upload fields):")
                    for fp in file_paths:
                        lines.append(f"- {fp.get('field_hint', 'unknown')} → {fp.get('path', '')}")
                    lines.append("")

                lines.extend(["=" * 60, ""])
                user_inputs_section = "\n".join(lines)

            # Screenshot section
            screenshot_section = ""
            if screenshot_base64:
                screenshot_section = """
🖼️ DOM AND SCREENSHOT GUIDANCE:
1. FILL ALL FIELDS (DO NOT SKIP ANY) BY EXAMINING THE DOM AND ALSO VIEWING THE SCREENSHOT
2. Extract ALL interactive elements from DOM - inputs, selects, textareas, checkboxes, radio buttons, clickable option cards, toggles, tabs, accordions, repeatable lists with "Add"/"+"/etc buttons, and any element a user would click or fill to complete the form
3. CHECK SCREENSHOT TO VIEW PAGE AND SEE ALL THE FIELDS AND LIST ITEMS - MUST NOT SKIP ANY FIELD
4. Generate steps for EVERY field and list item - do NOT skip any - first all fields in current tab then next tabs
5. Screenshot shows active tab/section and visual layout
6. BEFORE adding any navigation step (next tab, submit), re-check DOM and screenshot to ensure no field was skipped
7. **JUNCTION CHECK:** Look for dropdowns/radio buttons/etc in SCREENSHOT. If they could show/hide different fields based on selection, mark them as junctions (is_junction=true + junction_info).
"""

            # Build retry message section if present
            retry_message_section = ""
            if retry_message:
                retry_message_section = f"""
⚠️⚠️⚠️ CRITICAL RETRY MESSAGE ⚠️⚠️⚠️
{retry_message}
⚠️⚠️⚠️ END CRITICAL MESSAGE ⚠️⚠️⚠️

"""
            # Mapping hints from user
            hints_section = f"## AI GUIDANCE NOTES FROM USER\n{mapping_hints}\n\n" if mapping_hints else ""

            # ==================== BUILD THE PROMPT ====================

            prompt = f"""You are a web automation expert generating Selenium WebDriver test steps.

{hints_section}## FIRST: CHECK FOR VALIDATION ERRORS

Scan DOM and SCREENSHOT for validation errors (red boxes, error messages like "Please fill in", "required", "invalid", error classes).

**NOT validation errors (ignore these):**
- Colored field backgrounds (pink, red, yellow) that are just styling - not errors
- Required field indicators (* or colored labels)
- Empty fields that haven't been submitted yet

**If validation errors are visible, return ONLY:**
```json
{{{{
  "validation_errors_detected": true
}}}}
```

**If NO validation errors:** Continue below to SECOND check.

## SECOND: CHECK FOR PAGE ERRORS

Scan DOM and screenshot for unrecoverable state:
- "Page Not Found", "404", "Error", "Session Expired", "Access Denied", empty page
- "This site can't be reached", "refused to connect", "took too long to respond"
- "ERR_CONNECTION_REFUSED", "ERR_NAME_NOT_RESOLVED", "DNS_PROBE_FINISHED_NXDOMAIN"

**If page error detected, return ONLY:**
```json
{{{{
  "page_error_detected": true,
  "error_type": "page_not_found"
}}}}
```
(error_type: "page_not_found", "session_expired", "server_error", or "empty_page")

**If NO page errors:** Continue below to THIRD CHECK.

**⚠️ THIRD: CHECK FOR LOADING SPINNER**
If loading spinner is visible in screenshot, return ONLY the wait step:
```json
{{
  "steps": [
    {{"step_number": 1, "action": "wait_spinner_hidden", "selector": ".spinner-class", "value": "15", "description": "Wait for loading to complete", "full_xpath": "", "force_regenerate_verify": true}}
  ]
}}
```
Find spinner in DOM (patterns: spinner, loader, loading, progress, busy, pending, processing, circular, overlay, backdrop, or SVG/icon animations).
After spinner disappears, you will be called again to generate verify steps.

**If no spinner:** Continue below to FORTH CHECK.

**⚠️ FOURTH: CHECK IF FORM SUBMISSION COMPLETE**
If the last step in "Steps Already Completed" was a save/create/submit/accept/ok button:
1. Search DOM and SCREENSHOT for ALL VISIBLE Save/Submit/Create buttons on the page which saves your form page
2. Compare with "Steps Already Completed" to see which Save buttons were already clicked
3. If ANY VISIBLE Save/Submit button exists that was NOT already clicked → form is NOT complete, continue generating steps for remaining sections
4. ONLY if ALL Save/Submit buttons have been clicked → form is complete, RETURN ONLY:

```json
{{
  "steps": [
    {{"step_number": 1, "action": "wait_for_ready", "selector": "", "value": "2", "description": "Wait for page to stabilize after form submission", "full_xpath": "", "force_regenerate_verify": true}}
  ]
}}
```
This will trigger verification steps generation (mandatory - make sure you added to this json - "force_regenerate_verify": true).

**If more fields/buttons exist:** Continue below to generate remaining steps.


{screenshot_section}{critical_fields_section}{route_planning_section}
{user_inputs_section}
{retry_message_section}

## Current Context:

{executed_context}

## Current Page DOM:
{dom_html}

{test_cases_context}

## Your Task:
Generate the REMAINING steps to complete ONLY the test cases listed in "Test Cases" section above.


**⚠️ STOP WHEN COMPLETE:**
- Generate steps ONLY for test cases in the list - NEVER invent new ones (no TEST_4 if not listed)
- When all listed test cases are done, return empty steps array
- Ignore Edit/Delete/other buttons if no matching test case exists

**⚠️ CONTINUE FROM CURRENT STATE:**
The screenshot and DOM reflect the state AFTER all "Steps Already Completed" executed. Your first generated step should continue from this state, not repeat actions already done.
Some of the steps are atomic steps , So look at the last executed step to see if its atomic step and in such a case you need to continue it.
For example if the last step already executed was to open a drop down then your next step is to click at item in it

**⚠️ DO NOT RE-FILL ALREADY COMPLETED FIELDS:**
- Check "Steps Already Completed" above - these fields are DONE
- NEVER generate fill/select/check steps for fields that already appear in completed steps
- A field is "completed" ONLY if its EXACT selector appears in completed steps - do NOT assume

**⚠️ Never return to a previous Tab that you already filled

**⚠️ CRITICAL AND MANDATORY - DURING THE CREATION GIVE STEPS TO ALSO 100% OF ALL THE OPTIONAL FIELDS - MUST NOT SKIP ANY FIELD (ALL MANDATORIES FIELDS AND ALL OPTIONALS FIELDS)


**⚠️CRITICAL - SCAN THE SCREENSHOT IN ADDITION TO DOM **
- Locate the trigger step in SCREENSHOT
- Critical - look at the image - is there a dropdown that is currently open - if that was the last executed step that was done - if this is the case then you first step is to click an option from this list
- Analyze the SCREENSHOT to SEE ALL THE 100% remaining steps to perform to FILL EVERYTHING IN THE SCREENSHOT
- Look for fields that may appear outside blocks of fields in the current tab so they might be hard to find - we must find all of them
- Make sure you create steps for all of them
- Note that the trigger step might be at an inner location so you need to look also outside this trigger step's scope
- **JUNCTION CHECK:** Look for dropdowns/radio buttons/cards in SCREENSHOT. If they could show/hide different fields based on selection, mark them as junctions (is_junction=true + junction_info).


**Priority order:**
1. **CHECK CURRENT PAGE FIRST:** Look at DOM/SCREENSHOT - if you see a list/table, you're on list page. If you see read-only values, you're on detail page. Do NOT generate navigation to a page you're already on.
2. If previous step was next/continue button AND you see a blocking overlay... your first step should be wait_message_hidden
3. Complete current tab 100% before moving to next tab:
   - Fill ALL visible fields - check horizontally (side-by-side fields) and vertically
   - Interact with ALL elements - both required AND optional (inputs, selects, clickable option cards, toggles, text, date, email, textarea, comments, notes, etc.)
   - Click EVERY "Add" button you find (each may open a different sub-form or list)
   - Handle special inputs (dropdowns, checkboxes, sliders, file uploads, drag and drop)
   - Do NOT skip fields because they appear optional - fill EVERY visible field
4. Only after ALL fields AND ALL "Add" buttons in current tab are done, navigate to next tab
5. Submit form

**Forms with Multiple Save Sections:**
If you see multiple Save buttons within the form (one per section):
1. Fill all fields in current section
2. Click that section's Save button
3. Wait for save confirmation (if any)
4. Move to next section and repeat

**For edit/update tests:** Navigate → Verify original value → Update (fill auto-clears) → Navigate back

## Response Format:
```json
{{
  "steps": [
    {{"step_number": N, "action": "action", "selector": "selector", "value": "value", "description": "description", "full_xpath": "/html/body/.../element", "force_regenerate": false, "dont_regenerate": false}}
  ]
}}
```

---

**full_xpath field (MANDATORY FOR ALL STEPS):**
- Fallback selector if primary selector fails
- Must start from `/html/body/...`
- **COUNTING IS CRITICAL:** Count ALL direct children of each parent, including hidden elements, modals, overlays
- Double-check your count
- **USE IDs WHEN AVAILABLE:** If any element in the path has an ID, use it instead of counting:
  - ✅ `/html/body/div[@id='findingModal']/div/div[4]/button[2]`
  - ❌ `/html/body/div[3]/div/div[4]/button[2]`
- Only use indices `[n]` when no ID exists on that element
- Trace the path carefully from body → target element using the DOM

**❌ BAD full_xpath (NEVER DO THIS):**
`/html/body/div[1]/div/div[2]/div/div[1]/div/div[3]/div/div[1]/div[2]/div[1]/div/div[1]/div`
- All indices, ignores `id="app"` that exists in DOM!

**✅ GOOD full_xpath (USE IDs AND CLASSES):**
`/html/body/div[@id='app']//div[contains(@class,'oxd-form')]//div[contains(@class,'oxd-input-group')][1]//div[contains(@class,'oxd-select-text')]`
- Uses id="app" as anchor
- Uses class names from DOM
- Index only where truly needed

**⚠️ SELF-VERIFICATION (MANDATORY BEFORE RETURNING):**
For EACH full_xpath you generate, you MUST verify it by tracing through the DOM:

1. Start at `<body>` in the DOM
2. For each segment in your path (e.g., `/div[2]`):
   - Find that element in DOM
   - Confirm tag name matches
   - Confirm index is correct (count ALL children of same tag, including hidden)
   - If using `[@id='x']` or `[@class='x']`, confirm attribute exists and matches
3. Verify final element is your actual target

**Example verification:**
Your xpath: `/html/body/div[2]/form/div[3]/input[1]`

CHECK:
- body → has children: div#app, div#modal, script → div[2] = div#modal ✓ or ✗?
- div#modal → has children: div.header, form → form = form ✓
- form → has children: div, div, div, button → div[3] = third div ✓
- div[3] → has children: label, input, span → input[1] = first input ✓

If ANY check fails → FIX the xpath before returning.

---

**force_regenerate field (REQUIRED):**
- Set to `true` for navigation actions: Next, Continue, Edit, Delete, Back to List buttons
- Set to `false` for: fill, select, click tab, check, hover, scroll, ALL wait actions, switch_to_frame, switch_to_default

**Mandatory - dont_regenerate field:**
- Set to `true` ONLY for:
  * Filling a field (fill action)
  * Opening/closing modals or dialogs
  * Adding/removing items in a list or table
  * Saving an item in a list that was added
  * Expanding/collapsing accordion sections
- Set to `false` (or omit) for all other actions


** CRITICAL AND MANDATORY - force_regenerate field (for Save/Submit only):**
- Set to `true` for Save and Submit buttons

---

## Action Reference:

**Available actions:** fill, fill_autocomplete, select, click, double_click, check, uncheck, slider, range_slider, drag_and_drop, press_key, wait, wait_for_ready, wait_for_visible, wait_message_hidden, wait_spinner_hidden, scroll, hover, refresh, switch_to_frame, switch_to_default, switch_to_shadow_root, switch_to_window, switch_to_parent_window, create_file, upload_file

**⚠️ NEVER generate "verify" action** during the creation stage - verify steps are generated separately AFTER form submission. Use `wait_for_visible` if you need to confirm an element appeared.

**Context switching:**
- `switch_to_frame` / `switch_to_shadow_root`: Enter iframe or shadow DOM
- `switch_to_default`: Exit from iframe OR shadow DOM back to main page (ALWAYS use this to return)
- `switch_to_parent_window`: Switch between browser windows/tabs only (NOT for iframe/shadow DOM)

**wait_message_hidden:** ONLY after page-level navigation (Next Page, Submit Form) when blocking overlay covers >30% of page. Do NOT use for success toasts or floating messages.

**wait_spinner_hidden:** ONLY when blocking spinner/loader covers >30% of page. Provide selector from DOM.

**Selection elements - choose correct action:**
- `select` → ONLY for native `<select>` HTML tag (selector MUST be `select[...]` or `select#...`)
- `click` → For custom/styled dropdowns (div, span, or any non-select element - even if class contains "select")
- `check`/`uncheck` → For checkboxes

**⚠️ CUSTOM DROPDOWN DETECTION:** If element tag is `<div>`, `<span>`, or anything other than `<select>`, it's a CUSTOM dropdown:
- ❌ WRONG: `{{"action": "select", "selector": "//div[contains(@class, 'select')]"}}` (div is NOT a native select!)
- ✅ RIGHT: `{{"action": "click", "selector": "//div[contains(@class, 'select')]", "field_name": "Country", "force_regenerate": true}}` then click option

**Slider Actions:**
For sliders, provide only the rail/track selector - agent handles clicking and reading values:
```json
{{"action": "slider", "selector": "input[type='range']#volume", "description": "Set volume slider"}}
{{"action": "range_slider", "selector": ".price-range-track", "description": "Set price range filter"}}
```

**Drag and drop:** selector = element to drag, value = drop target
```json
{{"action": "drag_and_drop", "selector": "#dragItem", "value": "#dropZone", "description": "Drag item to zone"}}
```

**File upload:** Two steps required
```json
{{"action": "create_file", "file_type": "pdf", "filename": "test.pdf", "content": "Test content", "selector": "", "value": "", "description": "Create file"}}
{{"action": "upload_file", "selector": "input[type='file']", "value": "test.pdf", "description": "Upload file"}}
```
Supported types: pdf, txt, csv, xlsx, docx, json, png, jpg

=== DISCOVERY FIELDS (force_regenerate) ===

When generating a step, ask yourself:
"Can I see in the DOM what I need to interact with AFTER this action?"

- YES → Complete normally
- NO → Use force_regenerate: true, you'll be called again with updated DOM

**The Pattern:**
1. Trigger action (click/fill) + force_regenerate: true
2. System executes, waits for DOM to stabilize, re-extracts DOM
3. You're called again with updated DOM showing the revealed content
4. Generate the next step(s) with now-visible elements

**Common Discovery Scenarios:**
- Custom dropdown: options hidden until clicked
- Autocomplete: suggestions hidden until typing
- Date picker: calendar hidden until focused
- Any element that reveals hidden content on interaction

**Custom Dropdown Example (Only if it is not a native select dropdown):**
Step 1:
{{"action": "click", "selector": ".dropdown-trigger", "field_name": "gender", "description": "Open dropdown", "force_regenerate": true}}

Step 2 (after regeneration - options now visible):
{{"action": "click", "selector": "//li[contains(text(), 'Option A')]", "field_name": "male", "description": "Select Option A"}}

**⚠️ field_name (REQUIRED for ALL click and fill actions):**
For ALL click and fill actions, ALWAYS include `field_name` with the EXACT label text:
- `field_name` must match the field's label EXACTLY as shown on page (case-insensitive)
- Used as fallback if selector fails
- Example: If label shows "Car Type", use `"field_name": "Car Type"`
**Exception: for dropdown items field_name will be the dropdown item name

**Autocomplete Example:**
Step 1:
{{"action": "fill_autocomplete", "selector": "input#city", "value": "quattera", "description": "Type to trigger suggestions", "force_regenerate": true}}

Step 2 (after regeneration - suggestions now visible):
{{"action": "click", "selector": "//ul[@class='suggestions']/li[1]", "field_name": "City", "description": "Select first suggestion"}}

**RULE:** If you cannot see in the DOM what you need to select/click after an action, use force_regenerate: true.

=== COMPLEX FIELDS (Atomic Step Sequences) ===

Some fields require multiple atomic steps to complete.

**RULE:**
1. If the field matches a specific action type (select, slider, check, etc.) → use that action
2. If the field does NOT match any specific action type → examine the DOM and generate a sequence of atomic actions (click, fill, press_key, etc.)

**Examples:**
- Multiple input boxes (OTP/PIN) → fill each box separately
- Tag input requiring confirmation → fill + press_key ENTER

Analyze the DOM, understand the field's structure, and generate appropriate atomic steps.

---
**Junctions:** Mark a step as a junction if ANY of these are true:
- The element is one of several options the user can choose from (radio buttons, option cards, dropdown, tabs, toggle buttons, etc.)
- Selecting it MIGHT reveal/show different fields than selecting a sibling option
- The element looks like a choice/option/selection among alternatives

**When in doubt, mark it as a junction** - we verify junctions automatically with before/after screenshots, so false positives are OK but missing a junction is bad.

**Junction types:** dropdowns, radio buttons, checkboxes, toggle buttons, option cards, segmented controls, or any element where you choose ONE option from several alternatives.

**CRITICAL - ALWAYS MARK AS JUNCTION:**
- If you are clicking ONE of SEVERAL similar elements (e.g., one radio button among many, one card among several cards, one option among choices) → it IS a junction
- If the element is part of a group where user must choose ONE (radio group, option cards, tabs) → it IS a junction
- If clicking this element could potentially show different fields than clicking its sibling elements → it IS a junction
- If the element is part of a group where user must choose ONE and the choice affects which fields appear (radio group, option cards) → it IS a junction

**IMPORTANT:** When clicking any element that LOOKS LIKE it could show/hide different panels or field sets (e.g., it's one of several similar options, it's a tab, it's a radio button, it's an option card), mark it as a junction. Use the selector of the element you actually click for the action, and use the most relevant `name` or `id` attribute for `junction_name`.

**Junction format:**
```json
{{"action": "select", "selector": "...", "value": "...", "is_junction": true, "junction_info": {{"junction_name": "fieldName", "all_options": ["option1", "option2"], "chosen_option": "option1"}}, "description": "..."}}
```

**junction_info fields (ALL MANDATORY):**
- `junction_name`: Use element's `name` or `id` attribute
- `all_options`: List ALL available options from DOM - for `<select>` dropdowns, ONLY include values from actual `<option>` tags inside the `<select>`. Do NOT infer options from HTML comments, CSS classes, or JavaScript code.
- `chosen_option`: The option you are selecting

Always include `is_junction: true` and `junction_info` even when following junction instructions.
---


## Selector Rules:

**General selectors - prefer in this order:**
1. ID: `#fieldId` or `input#fieldId`
2. Name: `input[name='fieldName']`
3. Data attributes: `[data-testid='field']`
4. Unique class: `.unique-class-name`
5. XPath with attributes: `//button[@onclick='save()']`
6. XPath by label: `//label[contains(text(), 'Name')]/..//input`

**CRITICAL - SELECTOR MUST BE UNIQUE:**
- If ID/name/data-attr are missing or not clearly unique, use XPath scoped to parent container
- When in doubt, prefer more specific selector over simpler one
- **For multiple similar elements (e.g., multiple dropdowns with same class):**
  - ✅ GOOD: `(//div[@class='dropdown']//span)[1]` (correct index syntax - parentheses FIRST, then index)
  - ❌ WRONG: `//div[@class='dropdown'][1]//span` (index applies to child position, not result set)
  - ❌ NEVER: `//label[...]/..//div` or `//label[...]/following::div` - parent/following traversal breaks across apps

**Modal buttons - use XPath for precision:**
- `//div[contains(@class, 'modal')]//button[contains(text(), 'Save')]`
- `//div[contains(@class, 'modal')]//button[@type='submit']`

**Class matching:** Use `contains(@class, 'x')` not `@class='x'`


----

## Rules:
- Never use CSS `:contains()` or `:has()` - not supported in Selenium
- Never use `wait` with value > 10 seconds - use wait_for_ready instead
- Complete current tab before moving to next

---


Return ONLY the following JSON object (no other text):
```json
{{
  "steps": [...]
}}
```

"""

            # Call Claude API with retry (with or without screenshot)
            result_logger_gui.info("[AIHelper] Sending regeneration request to Claude API...")
            #print(f"[AIHelper] DEBUG - Prompt starts with: {prompt[:1700]}")
            #print(f"[AIHelper] DEBUG - Prompt starts with: {prompt}")

            if screenshot_base64:
                message_content = [
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
                #print("\n" + "!" * 80)
                #print("!!!!!!!!!!! REGENERATE_STEPS - (WITH IMAGE) FINAL PROMPT TO AI !!!!")
                #print("!" * 80)
                #import re
                #prompt_no_dom = re.sub(r'## Current Page DOM:.*?(?=\n[A-Z=\*#])',
                #                       '## Current Page DOM:\n[DOM REMOVED FOR LOGGING]\n\n', prompt,
                #                       flags=re.DOTALL)
                #print(prompt)
                #print("!" * 80 + "\n")
                #print("!*!*!*!*!*!*!*! Entering the AI func for Regenerate steps")
                # Debug mode: log full prompt (DOM truncated)
                if self.session_logger and self.session_logger.debug_mode:
                    import re
                    prompt_for_log = re.sub(r'## Current Page DOM:.*?(?=\n##|\n\*\*|$)',
                                            '## Current Page DOM:\n[DOM TRUNCATED]\n\n', prompt, flags=re.DOTALL)
                    self.session_logger.ai_call("regenerate_steps", prompt_size=len(prompt), prompt=prompt_for_log)

                response_text = self._call_api_with_retry_multimodal(message_content, max_tokens=16000,
                                                                     max_retries=3)
            else:
                response_text = self._call_api_with_retry(prompt, max_tokens=16000, max_retries=3)

            if response_text is None:
                print("[AIHelper] ❌ Failed to regenerate steps after retries")
                return {"steps": [], "ui_issue": "", "no_more_paths": False}

            print(f"[AIHelper] Received regeneration response ({len(response_text)} chars)")
            # Debug mode: log full raw response
            if self.session_logger and self.session_logger.debug_mode:
                self.session_logger.ai_response("regenerate_steps", success=True, response=response_text)

            # Parse JSON response
            import re


            ## DEBUG ###
            brace_count = 0
            json_end = 0
            in_json = False
            for i, char in enumerate(response_text):
                if char == '{':
                    if not in_json:
                        in_json = True
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0 and in_json:
                        json_end = i + 1
                        break
            first_json = response_text[:json_end] if json_end > 0 else response_text
            json_match = re.search(r'\{[\s\S]*\}', first_json)
            ## DEBUG ##


            ### original like ###
            #json_match = re.search(r'\{[\s\S]*\}', response_text)

            if json_match:
                response_data = json.loads(json_match.group())
                print(f"[AIHelper] DEBUG - Response keys: {response_data.keys()}")

                # Check if AI detected validation errors
                if response_data.get("validation_errors_detected"):
                    print(f"[AIHelper] ⚠️ !!!!!!! Validation errors detected in DOM/screenshot")
                    print(response_text)
                    return {
                        "steps": [],
                        "validation_errors_detected": True,
                        "ui_issue": "",
                        "no_more_paths": False
                    }

                # Check if AI detected page errors
                if response_data.get("page_error_detected"):
                    print(f"[AIHelper] ⚠️ !!!!!!! Page error detected in DOM/screenshot")
                    return {
                        "steps": [],
                        "page_error_detected": True,
                        "error_type": response_data.get("error_type", "unknown"),
                        "ui_issue": "",
                        "no_more_paths": False
                    }

                steps = response_data.get("steps", [])

                # DEBUG: Print full response when 0 steps returned to investigate why
                if len(steps) == 0:
                    print("=" * 80)
                    print("[AIHelper] ⚠️ DEBUG: REGENERATE RETURNED 0 STEPS")
                    print("=" * 80)
                    print(f"[AIHelper] Full AI response:\n{response_text}")
                    print("=" * 80)
                    # CloudWatch logging
                    if self.session_logger:
                        self.session_logger.warning(
                            f"!!!!! REGENERATE RETURNED 0 STEPS - Raw AI response: {response_text}",
                            category="ai_response"
                        )

                print(f"[AIHelper] Successfully regenerated {len(steps)} new steps")

                return {"steps": steps, "ui_issue": "", "no_more_paths": False}
            else:
                print("[AIHelper] No JSON object found in regeneration response")
                raise AIParseError("No JSON object found in regeneration response")



        except json.JSONDecodeError as e:
            print(f"[AIHelper] JSON parse error: {e}")
            print(f"[AIHelper] Raw response:\n{response_text}")

        except AIParseError:
            raise

        except Exception as e:
            print(f"[AIHelper] Error regenerating steps: {e}")
            import traceback
            traceback.print_exc()
            raise AIParseError(f"Unexpected error: {e}")

    def regenerate_verify_steps(
            self,
            dom_html: str,
            executed_steps: list,
            test_cases: list,
            test_context,
            screenshot_base64: Optional[str] = None,
            ai_parse_max_retries: int = 2,
    ) -> Dict[str, Any]:
        """
        Regenerate verification steps after Save/Submit - focused on verifying fields

        Args:
            dom_html: Current page DOM (after Save/Submit)
            executed_steps: Steps already executed (contains FILL/SELECT values to verify)
            test_cases: Test cases
            test_context: Test context
            screenshot_base64: Optional base64 screenshot for visual context

        Returns:
            Dict with 'steps' (list), 'ui_issue' (string), and 'no_more_paths' (bool)
        """
        try:
            print(f"[AIHelper] Regenerating VERIFY steps after Save/Submit...")
            print(f"[AIHelper] Already executed: {len(executed_steps)} steps")

            # Build context of what's been done - this is crucial for knowing what to verify
            executed_context = ""
            if executed_steps:
                executed_context = f"""
## Steps Already Completed:
{json.dumps([{"step": i + 1, "action": s.get("action"), "description": s.get("description"), "selector": s.get("selector"), "value": s.get("value")} for i, s in enumerate(executed_steps)], indent=2)}
"""

            # Build test cases context
            test_cases_context = ""
            if test_cases:
                test_cases_context = f"""
## Test Cases:
{json.dumps(test_cases, indent=2)}
"""

            # Screenshot section
            screenshot_section = ""
            if screenshot_base64:
                screenshot_section = """
🖼️ SCREENSHOT PROVIDED:
Use the screenshot to understand the current page layout and identify where field values are displayed.
**VALIDATION ERROR CHECK:** If you see validation errors (red borders, error messages, error classes like has-error/is-invalid), return ONLY `{"validation_errors_detected": true}`. Empty unfilled fields are NOT errors.
"""

            # ==================== BUILD THE VERIFICATION PROMPT ====================

            prompt = f"""You are a web automation expert generating Selenium WebDriver VERIFICATION test steps.

## FIRST: CHECK FOR VALIDATION ERRORS

Scan DOM and screenshot for validation errors (red boxes, error messages like "Please fill in", "required", "invalid", error classes).

**NOT validation errors (ignore these):**
- Colored field backgrounds (pink, red, yellow) that are just styling - not errors
- Required field indicators (* or colored labels)
- Empty fields that haven't been submitted yet

**If validation errors are visible, return ONLY:**
```json
{{{{
  "validation_errors_detected": true
}}}}
```

**If NO validation errors:** Continue below.

## SECOND: CHECK FOR PAGE ERRORS

Scan the DOM and screenshot for signs of unrecoverable state:
    - "Page Not Found", "404", "Not Found", "Error 404"
    - Empty page with no form elements
    - "Session Expired", "Access Denied", "Unauthorized"
    - Server error messages ("500", "Internal Server Error")
    - "This site can't be reached", "refused to connect", "took too long to respond"
    - "ERR_CONNECTION_REFUSED", "ERR_NAME_NOT_RESOLVED", "DNS_PROBE_FINISHED_NXDOMAIN"

**If page error detected, return ONLY:**
```json
{{{{
  "page_error_detected": true,
  "error_type": "page_not_found"
}}}}
```
(error_type: "page_not_found", "session_expired", "server_error", or "empty_page")

**If NO page errors:** Continue below.

## THIRD: CHECK FOR LOADING SPINNER

If loading spinner is visible in screenshot, return ONLY the wait_spinner_hidden step:
```json
{{{{
  "steps": [
    {{"step_number": 1, "action": "wait_spinner_hidden", "selector": ".spinner-class", "value": "15", "description": "Wait for loading to complete", "full_xpath": "", "force_regenerate_verify": true}}
  ]
}}}}
```
Find spinner in DOM (patterns: spinner, loader, loading, progress, busy, pending, processing, circular, overlay, backdrop, or SVG/icon animations).
After spinner disappears, you will be called to generate verify steps.

**If no spinner:** Continue with verification below.

---

## VERIFICATION MODE - AFTER SAVE/SUBMIT

You are now in VERIFICATION MODE. The form has been saved/submitted successfully.
Your task is to add verification steps.

{screenshot_section}
## Current Context:

{executed_context}

## Current Page DOM:
{dom_html}

{test_cases_context}

## Your Task:
Generate steps to VERIFY all fields that were filled during the test, plus any navigation needed to access view pages.

**What you must do:**
1. Look at "Steps Already Completed" - find ALL fill/select/check steps
2. For EACH field that was filled, generate a VERIFY step
3. If data is on a different page (e.g., need to click "View" button), add navigation steps
4. A field MAY be verified on BOTH list page AND detail page - but NEVER twice on the same page

**⚠️ CRITICAL - YOU MUST GENERATE VERIFY STEPS:**
- Your job is to OUTPUT verify step JSON objects, NOT to visually confirm data yourself
- MANDATORY - if you have all the verify steps in the already created list of steps then do not create them again.
- Even if you can SEE the correct values in the DOM/screenshot, you MUST generate verify steps (unless you already created verify steps for them)
- The verify steps will be EXECUTED by automation later - without them, nothing is verified
- Return `"steps": []` ONLY when verify steps were ALREADY GENERATED in previous calls (check "Steps Already Completed" for existing verify actions)
- If you see a detail/view page with data but NO verify steps in "Steps Already Completed", you MUST generate verify steps NOW

**Current page detection:**
- If you see a LIST/TABLE page, follow this EXACT order:
  1. **SEARCH (MANDATORY):** Check DOM for search input (`input[type='search']`, `input#search`, `input[placeholder*='Search']`). If exists → Generate fill step to search for record using unique value (name/email). If no search exists → Skip to step 2.
  2. **VERIFY COLUMNS:** Generate verify steps for visible table columns (use `//tr[1]//td[N]` selectors)
  3. **CLICK VIEW:** Generate click step for View button with `force_regenerate_verify: true`
- If you see a VIEW/DETAIL page: Generate `"action": "verify"` steps for ALL fields displayed on this page

**WHEN TO RETURN EMPTY STEPS `"steps": []`:**
Return empty ONLY if "Steps Already Completed" already contains `"action": "verify"` steps for the current page's fields.

**NO GOING BACKWARDS:**
- If "Steps Already Completed" shows you already clicked "View" and verified the detail page → You are DONE. Return empty steps.
- Do NOT click "Back to List" after verifying the detail page.
- The verification flow is ONE DIRECTION: List → View → Done. Never go back.

## Response Format:
```json
{{
  "steps": [
    {{"step_number": N, "action": "action", "selector": "selector", "value": "value", "description": "description", "full_xpath": "REQUIRED - see below", "force_regenerate": false, "force_regenerate_verify": false, "dont_regenerate": false}}
  ]
}}
```

---

## VERIFICATION RULES

**⚠️ CRITICAL - VIEW/DETAIL PAGE ≠ FORM PAGE:**
After clicking View/Edit/Details button, you are on a READ-ONLY display page:
- ❌ WRONG: `input#fieldName`, `select#type`, `textarea#notes` (FORM elements - won't exist!)
- ✅ RIGHT: Data is displayed in `<span>`, `<div>`, `<td>`, `<dd>`, `<p>` - CHECK THE DOM!
- ALWAYS examine the CURRENT DOM structure before generating verify selectors

**CREATE VERIFY STEPS FOR ALL FIELDS - NO SKIPPING:**
1. Look through "Steps Already Completed" for ALL fill/select/check steps
2. Generate a VERIFY step for EACH field that YOU FILLED (unless already verified on THIS page)
3. A field can be verified on BOTH list page AND detail page - but NEVER generate duplicate verify for the same field on the SAME page
4. Get expected values from the `value` field of those fill/select steps
5. NEVER verify system-generated fields (Reference ID, Status, timestamps, IDs, "Created At", "Updated At", "Saved Date")
6. **NEVER SKIP VERIFY STEPS** for fields you filled - Generate verify even if:
   - You suspect expected value might not match displayed value
   - The format might differ (e.g., date format differences)
   - The field seems empty or missing
   - Verification failures are VALID test results - we WANT to catch mismatches, not hide them

**⚠️ ONLY CREATE VERIFY STEPS FOR FIELDS YOU FILLED - NEVER INVENT:**
- ✅ ONLY generate verify steps for fields that have a corresponding fill/select/check in "Steps Already Completed"
- ❌ NEVER verify that a field is "empty", "disabled", or "blank" - verify POSITIVE values only
- ❌ NEVER invent fields to verify - if you didn't fill it, don't verify it

**⚠️ CRITICAL - WHERE TO GET EXPECTED VALUES:**
- ✅ Get expected value from the `value` field in "Steps Already Completed" (what was ENTERED)
- ❌ NEVER use values from the current DOM (what is DISPLAYED) as expected values
- The whole point of verification is to CHECK if what was entered matches what is displayed
- Example: If fill step had `"value": "15-1-1990"`, verify with `"value": "15-1-1990"` - NOT what DOM shows

**How verify works:** Selector finds element by LOCATION. The `value` field contains expected text.

**BUILD SELECTOR FROM THE DOM - Common patterns:**
- By data attribute: `//div[@data-field='email']`
- By class and label: `//div[contains(@class, 'field-group')][.//label[contains(text(), 'Email')]]//div[contains(@class, 'field-value')]`
- By container filter: `//div[contains(@class, 'form-group')][.//label[contains(text(), 'Email')]]//input`

**⚠️ NEVER use `..` (parent traversal) or `following-sibling`** - these assume DOM structure and break across different apps.
- ❌ WRONG: `//label[contains(text(), 'Email')]/../div`
- ❌ WRONG: `//div[contains(@class, 'oxd-input-group')]//label[contains(text(), 'Employee')]/..//input`
- ❌ WRONG: ANY selector containing `/../` or `/..` - NEVER USE PARENT TRAVERSAL
- ✅ RIGHT: `//div[contains(@class, 'oxd-input-group')][.//label[contains(text(), 'Employee')]]//input`
- ✅ RIGHT: Use `[.//label[...]]` as a FILTER on the container, NOT `//label[...]/../`

**VERIFY SELECTOR EXAMPLES:**
- ✅ `//div[contains(@class, 'form-group')][.//label[contains(text(), 'Email')]]//span`
- ✅ `//div[contains(@class, 'field')][.//label[contains(text(), 'Name')]]//div[@class='value']`

Find the NEAREST container that holds BOTH label AND value, then filter by label and find value inside.

**⚠️ CRITICAL AND MANDATORY - SELECTOR MUST INCLUDE FIELD IDENTIFIER:**
Every verify selector MUST include the field name/label as an anchor (e.g., 'Email', 'First Name', 'Phone').
- ✅ `//div[contains(@class, 'field-group')][.//label[contains(text(), 'Email')]]//div[@class='value']`  
- ❌ `(//div[@class='field-value'])[3]` - position-only without field name won't work if layout changes

**⚠️ DUPLICATE FIELD NAMES (e.g., two "City" fields):**
When the same field label appears multiple times, scope the selector to the SECTION/PARENT container:
- ✅ `//div[contains(@class, 'personal-info')]//div[.//label[contains(text(), 'City')]]//span`
- ✅ `//section[@id='shipping']//div[.//label[contains(text(), 'City')]]//span`
- ✅ `(//div[.//label[contains(text(), 'City')]]//span)[1]` - use index as last resort
- ❌ `//label[contains(text(), 'City')]/..//span` - not unique when multiple exist

**TABLE/LIST verification - MANDATORY FOR IT TO SUCCEED -> SEARCH FIRST:**
Before generating ANY verify steps for a list/table, check for search input:
1. Look for search box in DOM: `input[type='search']`, `input#search`, `input[placeholder*='Search']`, `input[placeholder*='Filter']`
2. If search exists: Generate fill step to search, then wait_for_ready, then verify steps
3. If NO search exists: Use positional selectors on first row (newly added items typically appear at top)

**Why search first:** Positional selectors like `//tr[1]//td[1]` may fail on re-runs if multiple records exist. Searching isolates your record.

**Example with search:**
1. `{{"action": "fill", "selector": "input#searchBox", "value": "john@email.com", "description": "Search for created record", "force_regenerate_verify": true}}`
2. `{{"action": "wait_for_ready", "selector": "table", "description": "Wait for search results"}}`
3. `{{"action": "verify", "selector": "//table//tbody//tr[1]//td[1]", "value": "John", "description": "Verify name"}}`

**Positional selectors (use after search, or if no search available):**
- First data row, column 1: `//table//tbody//tr[1]//td[1]`
- First data row, column 2: `//table//tbody//tr[1]//td[2]`
- Last row (newly added): `(//table//tbody//tr)[last()]//td[1]`
- By row with unique class: `//tr[contains(@class,'highlight')]//td[1]`


**❌ WRONG selectors:**
- `//div[contains(text(), 'john@email.com')]` - value in selector!
- `//td[text()='TestValue']` - value in selector won't work with different test data!
- `//tr[td[text()='SomeValue']]//td[2]` - finding row by value won't work for reusable tests!
- `input#email` on view page - form elements don't exist on view pages!
- Inventing class names not in DOM

**⚠️ TABLE SELECTOR RULE:** Selectors must work with ANY test data. Use POSITION (row/column index) or STRUCTURE (classes, data-attributes), NEVER the actual field VALUES.

**Class matching:** Use `contains(@class, 'x')` not `@class='x'`

---

## Navigation Rules (for accessing view pages):

**Available actions:** click, verify, wait, wait_for_ready, wait_for_visible, wait_message_hidden, wait_spinner_hidden, scroll, select, hover, switch_to_frame, switch_to_default

**Selector preference order:**
1. ID: `#buttonId` or `button#viewBtn`
2. Data attributes: `[data-testid='view-button']`
3. Unique class: `button.view-btn`
4. XPath with attributes: `//button[@onclick='viewForm(0)']`
5. XPath by text: `//button[contains(text(), 'View')]`

**Modal buttons - use XPath for precision:**
- `//div[contains(@class, 'modal')]//button[contains(text(), 'View')]`

**force_regenerate_verify field (stay in verification mode):**
- Set to `true` for ANY navigation step that leads to a page with MORE fields to verify:
  * Click "View" button to see detail page → `force_regenerate_verify: true`
  * Click row in table to see details → `force_regenerate_verify: true`
  * Fill search box to filter list → `force_regenerate_verify: true`
  * ANy other action that is related to the list/view pages → `force_regenerate_verify: true`
  * wait_spinner_hidden so verification continues after wait completes
- Set to `false` for verify steps , final navigation (no more verification needed)
- ⚠️ IMPORTANT: If clicking a button will show NEW fields to verify, use `force_regenerate_verify: true`, NOT `force_regenerate: true`

**force_regenerate field (exit verification mode):**
- Set to `true` ONLY when ALL verification is complete and ALL verification pages are complete AND next test case requires Edit/Update
- Use this to transition from verification to the next test case (e.g., Edit test)

**How to decide:**
1. If more fields to verify on another page → use `force_regenerate_verify: true`
2. If ALL fields verified and all Verification pages are done AND next test is Edit/Update → use `force_regenerate: true` on Edit button

---------

**full_xpath field - REQUIRED FOR ALL ACTIONS INCLUDING VERIFY:**
- Fallback selector if primary selector fails
- Must start from `/html/body/...` and go DOWN the tree
- **MUST include field name filter** (e.g., `[.//label[contains(text(),'Employee')]]`)
- **USE IDs WHEN AVAILABLE:** If any element in the path has an ID, use it instead of counting:
  - ✅ `/html/body/div[@id='app']//form//div[contains(@class,'oxd-input-group')][.//label[contains(text(),'Employee')]]//input`
  - ❌ `/html/body/div[1]/div/div[2]/div[3]/input` (positional without field identifier!)

**❌ BAD full_xpath for verify (NEVER DO THIS):**
- `/html/body/div[1]/div/div[2]/div/div[1]/div/div[3]/input` - no field identifier, wrong field if layout changes!
- ANY path containing `/../` - parent traversal forbidden!

**✅ GOOD full_xpath for verify:**
`/html/body/div[@id='app']//form//div[contains(@class,'oxd-input-group')][.//label[contains(text(),'Employee')]]//input`
- Uses id="app" as anchor
- Uses class names from DOM
- **Includes field label filter** - finds correct field even if position changes

**⚠️ SELF-VERIFICATION (MANDATORY BEFORE RETURNING):**
For EACH full_xpath you generate, you MUST verify it by tracing through the DOM:

1. Start at `<body>` in the DOM
2. Trace your path segment by segment
3. Confirm the field label filter `[.//label[contains(text(),'X')]]` matches the field you're verifying
4. Verify final element contains/displays the expected value

If ANY check fails → FIX the xpath before returning.

---

## Rules:
- Never use CSS `:contains()` or `:has()` - not supported in Selenium
- Focus on VERIFICATION - this is not for filling forms
- Verify ALL fields from the test, including: text, dates, dropdowns, checkboxes, file uploads
- Navigate between pages as needed to verify all data

Return ONLY the JSON object.
"""

            # Call Claude API with retry (with or without screenshot)
            result_logger_gui.info("[AIHelper] Sending verify regeneration request to Claude API...")

            if screenshot_base64:
                message_content = [
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

                if self.session_logger and self.session_logger.debug_mode:
                    import re
                    prompt_for_log = re.sub(r'## Current DOM:.*?(?=\n##|\n\*\*|$)',
                                            '## Current DOM:\n[DOM TRUNCATED]\n\n', prompt, flags=re.DOTALL)
                    self.session_logger.ai_call("regenerate_verify_steps", prompt_size=len(prompt),
                                                prompt=prompt_for_log)

                response_text = self._call_api_with_retry_multimodal(message_content, max_tokens=16000,
                                                                     max_retries=3)
            else:
                response_text = self._call_api_with_retry(prompt, max_tokens=16000, max_retries=3)

            print(response_text)

            if response_text is None:
                print("[AIHelper] ❌ Failed to regenerate verify steps after retries")
                return {"steps": [], "ui_issue": "", "no_more_paths": False}

            print(f"[AIHelper] Received verify regeneration response ({len(response_text)} chars)")
            # Debug mode: log full raw response
            if self.session_logger and self.session_logger.debug_mode:
                self.session_logger.ai_response("regenerate_verify_steps", success=True, response=response_text)

            # Parse JSON response - find JSON with "steps" key
            remaining = response_text
            response_data = None

            while remaining:
                brace_count = 0
                json_start = -1
                json_end = 0
                in_json = False

                for i, char in enumerate(remaining):
                    if char == '{':
                        if not in_json:
                            in_json = True
                            json_start = i
                        brace_count += 1
                    elif char == '}':
                        brace_count -= 1
                        if brace_count == 0 and in_json:
                            json_end = i + 1
                            break

                if json_end == 0 or json_start == -1:
                    break

                try:
                    candidate = remaining[json_start:json_end]
                    parsed = json.loads(candidate)

                    # If validation errors detected, return immediately
                    if parsed.get("validation_errors_detected") == True:
                        print(f"[AIHelper] ⚠️ !!!!!!! Validation errors detected in DOM/screenshot")
                        return {
                            "steps": [],
                            "validation_errors_detected": True,
                            "ui_issue": "",
                            "no_more_paths": False
                        }

                    # If page error detected, return immediately
                    if parsed.get("page_error_detected") == True:
                        print(f"[AIHelper] ⚠️ !!!!!!! Page error detected in DOM/screenshot")
                        return {
                            "steps": [],
                            "page_error_detected": True,
                            "error_type": parsed.get("error_type", "unknown"),
                            "ui_issue": "",
                            "no_more_paths": False
                        }

                    # If this JSON has steps, use it
                    if "steps" in parsed:
                        response_data = parsed
                        break

                    # Otherwise continue searching
                    remaining = remaining[json_end:]

                except json.JSONDecodeError:
                    remaining = remaining[json_end:]
                    continue

            if response_data:
                steps = response_data.get("steps", [])
                print(f"[AIHelper] Successfully regenerated {len(steps)} verify steps")

                # DEBUG: Print full response when 0 steps returned to investigate why
                if len(steps) == 0:
                    print("=" * 80)
                    print("[AIHelper] ⚠️ DEBUG: VERIFY REGENERATE RETURNED 0 STEPS")
                    print("=" * 80)
                    print(f"[AIHelper] prompt given to AI:\n{prompt}")
                    print(f"[AIHelper] Full AI response:\n{response_text}")
                    print("=" * 80)
                    # CloudWatch logging
                    if self.session_logger:
                        self.session_logger.warning(
                            f"!!!!! VERIFY REGENERATE RETURNED 0 STEPS - Raw AI response: {response_text}",
                            category="ai_response"
                        )

                return {"steps": steps, "ui_issue": "", "no_more_paths": False}
            else:
                print(f"[AIHelper] No JSON with 'steps' key found. Raw response:\n{response_text[:2000]}")
                raise AIParseError("No JSON with 'steps' key found in verify regeneration response")

        except json.JSONDecodeError as e:
            print(f"[AIHelper] JSON parse error: {e}")
            print(f"[AIHelper] Raw response:\n{response_text}")
            raise AIParseError(f"JSON parse error: {e}")

        except AIParseError:
            raise

        except Exception as e:
            print(f"[AIHelper] Error regenerating verify steps: {e}")
            import traceback
            traceback.print_exc()
            raise AIParseError(f"Unexpected error: {e}")

    def discover_test_scenarios(self, dom_html: str, already_tested: list, max_scenarios: int = 5) -> list:
        """
        AI analyzes page and discovers new test scenarios

        Args:
            dom_html: Current page DOM
            already_tested: List of features already tested
            max_scenarios: Maximum scenarios to discover

        Returns:
            List of discovered test scenarios
        """
        try:
            already_tested_str = ", ".join(already_tested) if already_tested else "None"

            prompt = f"""Analyze this form page and discover {max_scenarios} NEW testable scenarios.

    === CURRENT PAGE DOM ===
    {dom_html}

    === ALREADY TESTED FEATURES ===
    {already_tested_str}

    === TASK ===
    Discover {max_scenarios} NEW test scenarios that are:
    1. NOT in the already-tested list
    2. Actually visible/available on this page
    3. Testable with automated steps
    4. Valuable for quality assurance

    For each scenario, provide:
    - Scenario name (brief, descriptive)
    - Why it's important to test
    - Priority (high/medium/low)
    - Test steps as simple string descriptions

    === OUTPUT FORMAT ===
    Return ONLY a JSON array (no other text):
    [
      {{
        "name": "Feature Name",
        "reason": "Why this should be tested",
        "priority": "high",
        "steps": [
          "Step 1 description as simple string",
          "Step 2 description as simple string",
          "Step 3 description as simple string"
        ]
      }}
    ]

    Example steps format:
    - "Navigate to form page"
    - "Fill all required fields in personal info section"
    - "Select option from dropdown that reveals additional fields"
    - "Fill conditional fields that appeared"
    - "Add list items"
    - "Click next to go to payment section"
    - "Complete payment fields"
    - "Submit form"
    - "Verify success confirmation"

    Focus on:
    - Unused form fields or sections
    - Different paths through conditional logic
    - List items
    - Alternative dropdown/radio selections
    - Edge cases or validation scenarios
    - Multi-step form flows

    ONLY return the JSON array, nothing else.
    """

            logger.info("Sending discovery request to Claude API...")

            response_text = self._call_api_with_retry(prompt, max_tokens=4096, max_retries=3)
            
            if response_text is None:
                logger.error("Failed to discover scenarios after retries")
                return []

            logger.info(f"Received discovery response ({len(response_text)} chars)")

            # Parse JSON
            import re

            # Try to extract JSON array from response
            json_match = re.search(r'\[[\s\S]*\]', response_text)
            if json_match:
                scenarios = json.loads(json_match.group())
                logger.info(f"Successfully discovered {len(scenarios)} scenarios")
                return scenarios
            else:
                logger.warning("No JSON array found in discovery response")
                return []

        except Exception as e:
            logger.error(f"Error discovering scenarios: {e}")
            return []

    def analyze_failure_and_recover(
            self,
            failed_step: Dict,
            executed_steps: List[Dict],
            fresh_dom: str,
            screenshot_base64: str,
            test_cases: List[Dict],
            test_context,
            attempt_number: int,
            recovery_failure_history: List[Dict] = None,
            error_message: str = ""
    ) -> List[Dict]:
        """
        Analyze a failed step using AI with vision and generate recovery steps
        
        Args:
            failed_step: The step that failed
            executed_steps: Steps completed successfully so far
            fresh_dom: Current DOM state
            screenshot_base64: Base64 encoded screenshot for visual context
            test_cases: Active test cases
            test_context: Test context
            attempt_number: Attempt number (1 or 2)
            recovery_failure_history: List of previous failures for detecting repeated issues
            
        Returns:
            List of steps: [recovery steps] + [corrected failed step] + [remaining steps]
        """
        import base64
        import re
        
        try:
            if self.session_logger:
                self.session_logger.info("🤖 !*!*!*! Entering FORM MAPPER prompter: analyze_failure_and_recover",
                                         category="ai_routing")

            print(f"[AIHelper] Analyzing failure with vision...")
            
            # Read and encode screenshot
            screenshot_data = screenshot_base64
            
            # Build the prompt
            prompt = self._build_recovery_prompt(
                failed_step=failed_step,
                executed_steps=executed_steps,
                fresh_dom=fresh_dom,
                test_cases=test_cases,
                test_context=test_context,
                attempt_number=attempt_number,
                recovery_failure_history=recovery_failure_history,
                error_message=error_message
            )
            
            # Call Claude with vision and retry logic
            result_logger_gui.info("[AIHelper] Sending failure recovery request to Claude API with vision...")
            
            content = [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/png",
                        "data": screenshot_data
                    }
                },
                {
                    "type": "text",
                    "text": prompt
                }
            ]

            #print("\n" + "!" * 80)
            #print("!!!!!!!! ANALYZE_FAILURE_AND_RECOVER - FINAL PROMPT TO AI !!!!")
            #print("!" * 80)
            #import re
            #prompt_no_dom = re.sub(r'## Current DOM:.*', '## Current DOM:\n[DOM REMOVED FOR LOGGING]\n', prompt,
            #                       flags=re.DOTALL)
            #print(prompt_no_dom)
            #print("!" * 80 + "\n")

            print("!*!*!*!*!*!*!*! Entering the AI func for analyze failures and recover")
            # Debug mode: log full prompt (DOM truncated)
            if self.session_logger and self.session_logger.debug_mode:
                import re
                prompt_for_log = re.sub(r'## Current DOM:.*?(?=\n##|\n\*\*|$)', '## Current DOM:\n[DOM TRUNCATED]\n\n',
                                        prompt, flags=re.DOTALL)
                self.session_logger.ai_call("analyze_failure_and_recover", prompt_size=len(prompt),
                                            prompt=prompt_for_log)

            response_text = self._call_api_with_retry_multimodal(content, max_tokens=16000, max_retries=3)
            #print(f"[DEBUG] Raw AI response: {response_text[:500]}...")
            
            if response_text is None:
                print("[AIHelper] ❌ Failed to get recovery response after retries")
                logger.error("[AIHelper] Failed to get recovery response after retries")
                return []
            
            print(f"[AIHelper] Received recovery response ({len(response_text)} chars)")
            logger.info(f"[AIHelper] Received recovery response ({len(response_text)} chars)")
            # Debug mode: log full raw response
            if self.session_logger and self.session_logger.debug_mode:
                self.session_logger.ai_response("analyze_failure_and_recover", success=True, response=response_text)

            # Strip markdown code blocks first
            clean_response = response_text
            if '```json' in clean_response:
                clean_response = clean_response.split('```json')[1].split('```')[0]
            elif '```' in clean_response:
                clean_response = clean_response.split('```')[1].split('```')[0]

            # Check if validation errors detected (returns dict instead of array)
            try:
                response_obj = json.loads(clean_response.strip())
                if isinstance(response_obj, dict) and response_obj.get("validation_errors_detected"):
                    print(
                        f"[AIHelper] ⚠️ Validation errors detected in step recovery - routing to validation error handler")
                    logger.warning(f"[AIHelper] ⚠️ Validation errors detected in step recovery")
                    return {"validation_errors_detected": True}

                if isinstance(response_obj, dict) and response_obj.get("page_error_detected"):
                    print(f"[AIHelper] ⚠️ Page error detected in step recovery")
                    logger.warning(f"[AIHelper] ⚠️ Page error detected in step recovery")
                    return {"page_error_detected": True, "error_type": response_obj.get("error_type", "unknown")}

            except json.JSONDecodeError:
                pass  # Not a simple dict, continue with array parsing

            # Extract JSON from response
            json_match = re.search(r'\[[\s\S]*\]', clean_response)
            if json_match:
                recovery_steps = json.loads(json_match.group())
                print(f"[AIHelper] Successfully parsed {len(recovery_steps)} recovery steps")
                logger.info(f"[AIHelper] Successfully parsed {len(recovery_steps)} recovery steps")
                return recovery_steps
            else:
                print("[AIHelper] No JSON array found in recovery response")
                logger.warning("[AIHelper] No JSON array found in recovery response")
                return []
                
        except Exception as e:
            print(f"[AIHelper] Error in failure recovery: {e}")
            print(f"[AIHelper] Raw response was: {response_text[:1000] if response_text else 'None'}")
            logger.error(f"[AIHelper] Error in failure recovery: {e}")
            return []

    def _build_recovery_prompt(
            self,
            failed_step: Dict,
            executed_steps: List[Dict],
            fresh_dom: str,
            test_cases: List[Dict],
            test_context,
            attempt_number: int,
            recovery_failure_history: List[Dict] = None,
            error_message: str = None
    ) -> str:
        """Build the prompt for failure recovery analysis - ONLY fix steps, not remaining steps"""

        action = failed_step.get('action', 'unknown')
        selector = failed_step.get('selector', '')
        description = failed_step.get('description', '')
        expected_value = failed_step.get('value', '')
        is_junction = failed_step.get('is_junction', False)
        junction_info = failed_step.get('junction_info', {})

        # Build executed steps context (last 5 steps for context)
        executed_context = ""
        if executed_steps:
            recent_steps = executed_steps[-5:] if len(executed_steps) > 5 else executed_steps
            executed_context = f"""
    ## Recent Executed Steps:
    {json.dumps([{"step": i + 1, "action": s.get("action"), "description": s.get("description"), "selector": s.get("selector")} for i, s in enumerate(recent_steps)], indent=2)}

    ⚠️ **VERIFY THESE STEPS:** Check screenshot/DOM - did the last 2-3 steps ACTUALLY achieve their effect?
    - hover/click: Did menu/dropdown/modal open and is it STILL visible?
    - select: Is the option actually selected?
    - fill: Is the value in the field?
    If a previous step's effect is MISSING, redo it first before fixing the failed step.
    """

        # Build recovery failure history section
        failure_history_section = ""
        if recovery_failure_history and len(recovery_failure_history) > 0:
            failure_history_section = f"""
    ## ⚠️ Previous Recovery Attempts Failed:
    {json.dumps(recovery_failure_history, indent=2)}

    If 4+ failures on same action, return EMPTY array [] to signal unrecoverable.
    """

        prompt = f"""# STEP FAILURE RECOVERY

    ## STEP 1: CHECK FOR VALIDATION ERRORS (MANDATORY)

    Scan the DOM for any error elements - look for:
    - Elements with "error" in class name (error-message, error, validation-error, has-error, is-invalid, field-error)
    - Text containing "Validation Error", "Please fill", "required", "must be", "invalid"
    - Red/orange styled error boxes or messages
    
    **NOT validation errors (ignore these):**
    - Colored field backgrounds (pink, red, yellow) that are just styling - not errors
    - Required field indicators (* or colored labels)
    - Empty fields that haven't been submitted yet

    **If ANY validation errors exist, return ONLY:**
    ```json
    {{{{
      "validation_errors_detected": true
    }}}}
    ```

    **DO NOT generate any steps if validation errors exist.**

    **Only if NO validation errors exist:** Continue to Step 1b below.
    
    ## STEP 1b: CHECK FOR UNRECOVERABLE PAGE STATE
    
    Scan the DOM and screenshot for signs of unrecoverable state:
    - "Page Not Found", "404", "Not Found", "Error 404"
    - Empty page with no form elements
    - "Session Expired", "Access Denied", "Unauthorized"
    - Server error messages ("500", "Internal Server Error")
    - "This site can't be reached", "refused to connect", "took too long to respond"
    - "ERR_CONNECTION_REFUSED", "ERR_NAME_NOT_RESOLVED", "DNS_PROBE_FINISHED_NXDOMAIN"
    
    **If page is unrecoverable, return ONLY:**
    ```json
    {{{{
      "page_error_detected": true,
      "error_type": "page_not_found"
    }}}}
    ```
    (use error_type: "page_not_found", "session_expired", "server_error", or "empty_page")
    
    **Only if page state is normal:** Continue to Step 1c below.

    ## STEP 1c: CHECK FOR LOADING SPINNER
    
    Look at screenshot for any rotating/spinning loading indicator that blocks interaction.
    
    **If loading spinner is visible, return:**
    ```json
    [
      {{"step_number": 1, "action": "wait_spinner_hidden", "selector": ".spinner-selector-from-dom", "value": "15", "description": "Wait for loading spinner to disappear", "full_xpath": ""}}
    ]
    ```
    Find spinner in DOM by looking at screenshot to identify visual indicator. Common patterns: spinner, loader, loading, progress, wait, busy, pending, processing, circular, overlay, backdrop, or SVG/icon animations.
    
    **Only if no spinner visible:** Continue to Step 2 below.

    ---

    ## STEP 2: FIX THE FAILED STEP

    🖼️ **Screenshot and DOM provided.** DOM is primary source, screenshot for visual verification.

    **Task:** Fix the failed step. Return ONLY fix steps (1-5 max). Do NOT generate remaining form steps.

    ## Failed Step (Attempt {attempt_number}/2):
    - Action: {action}
    - Selector: {selector}  
    - Description: {description}
    - Error: {error_message}
    {f"- Expected Value: {expected_value}" if action == "verify" and expected_value else ""}
    {f"- IS JUNCTION: This step is a junction - you MUST include is_junction: true and junction_info in your recovery step. junction_info: {json.dumps(junction_info)}" if is_junction else ""}
    {f"- HAS force_regenerate: true - your recovery step MUST also include force_regenerate: true" if failed_step.get('force_regenerate') else ""}
    {executed_context}
    {failure_history_section}
    ## Current DOM:
    ```html
    {fresh_dom}
    ```

    ---
    
    ## Special Case - VERIFY Action Recovery:
    If the failed action is `verify`:
    - Return EXACTLY 1 step with the FIXED selector
    - Keep the SAME expected value (the `value` field) - do NOT change it
    - Only fix the LOCATOR (selector)
    - Use empty string for full_xpath: `"full_xpath": ""`
    
    **VERIFY selector rules:**
    - Build selector from DOM structure, NOT from displayed values
    - Use `contains(@class, 'x')` not `@class='x'` (elements often have multiple classes)
    - View/detail pages use `<div>`, `<span>`, `<td>`, `<p>` - NOT form elements like `input`, `select`
    
    **✅ CORRECT verify selectors - VIEW/DETAIL pages:**
    - By label proximity: `//div[contains(@class, 'field-group')][.//div[contains(@class, 'field-label')][contains(text(), 'Email')]]//div[contains(@class, 'field-value')]`
    - By data attribute: `//div[@data-field='email']`
    
    **✅ CORRECT verify selectors - TABLE/LIST pages (use POSITIONAL):**
    - First row, column 1: `//table//tbody//tr[1]//td[1]`
    - Last row (newly added): `(//table//tbody//tr)[last()]//td[1]`
    - By row class: `//tr[contains(@class,'highlight')]//td[1]`
    
    **❌ WRONG verify selectors - NEVER use value in selector:**
    - `//div[contains(text(), 'john@email.com')]` - value in selector!
    - `//td[text()='TestValue']` - value in selector!
    - `//tr[td[text()='SomeValue']]//td[2]` - finding row by value!
    - `input#email` - form elements don't exist on view pages!
    - `@class='field-value'` - use `contains(@class, 'field-value')` instead
    
    
    ## Common Fixes by Error Type:

    **Element not found:**
    - Selector may be wrong - check DOM for correct id/class/name
    - Element inside iframe → switch_to_frame first
    - Element in shadow DOM → switch_to_shadow_root first

    **Element not interactable / not clickable:**
    - Hidden in collapsed section → click parent to expand first
    - Hidden in hover menu → hover on trigger element first  
    - Hidden in closed dropdown → click dropdown trigger first
    - Covered by overlay/tooltip → dismiss it first (click elsewhere or ESC)
    - Element disabled → enable via checkbox/toggle first
    - Outside viewport → scroll to element first

    **Selector not unique:**
    - ✅ GOOD - Scope to parent: `//div[@id='container']//button[text()='Save']`
    - ✅ GOOD - Use index (CORRECT syntax): `(//button[@class='submit'])[1]` (parentheses FIRST, then index)
    - ❌ WRONG index syntax: `//button[@class='submit'][1]` (index applies to child position, not result set)
    - ❌ NEVER: `//label[...]/..//div` or `//label[...]/following::div` - parent/following traversal breaks across apps

    **Stale element:**
    - Page refreshed - add wait, retry same selector

    **Wrong context:**
    - Inside iframe → switch_to_frame first
    - Need main page → switch_to_default first
    
        
    ## Selector Priority:
    1. ID: `#fieldId`
    2. Name: `[name='fieldName']`
    3. Scoped XPath: `//parent[@id='x']//child`

    Use `contains(@class, 'x')` not `@class='x'` for partial class match.

    ## Response Format:
    Return ONLY a JSON array with 1-5 fix steps:
    ```json
            [
              {{"step_number": 1, "action": "hover", "selector": "#trigger", "value": "", "description": "Re-hover to open menu", "full_xpath": "/html/body/div[@id='app']/div/nav/button"}},
              {{"step_number": 2, "action": "fill", "selector": "#field", "value": "test", "description": "Fill field in now-visible menu", "full_xpath": "/html/body/div[@id='app']/div/form/input[2]"}}
            ]
    ```
    
    ## ⚠️ full_xpath - MANDATORY FOR NON-VERIFY ACTIONS:
    For `verify` action recovery: use empty string `"full_xpath": ""`
    For all other actions: full_xpath is critical as fallback since original selector FAILED.
    
    **Rules:**
    - Must start from `/html/body/...`
    - **USE IDs WHEN AVAILABLE:** `/html/body/div[@id='app']/...` NOT `/html/body/div[1]/...`
    - Count ALL direct children including hidden elements, modals, overlays
    - Use `contains(@class, 'x')` for class matching
    
    **SELF-VERIFICATION (MANDATORY):**
    After constructing each full_xpath, trace it step-by-step through the DOM to verify:
    1. Does the path start correctly from body?
    2. Did you use IDs where available?
    3. Did you count child indices correctly?
    4. Does the final element match your target?
    
    If unsure, recount. A wrong full_xpath defeats the purpose of recovery.
    
    **❌ BAD full_xpath (NEVER DO THIS):**
    `/html/body/div[1]/div/div[2]/div/div[1]/div/div[3]/div/div[1]/div[2]/div[1]/div/div[1]/div`
    - All indices, ignores `id="app"` that exists in DOM!

    **✅ GOOD full_xpath (USE IDs AND CLASSES):**
    `/html/body/div[@id='app']//div[contains(@class,'oxd-form')]//div[contains(@class,'oxd-input-group')][1]//div[contains(@class,'oxd-select-text')]`
    - Uses id="app" as anchor
    - Uses class names from DOM
    - Index only where truly needed
    
    ## Important - Save/Submit Buttons:
    If the recovery step is clicking the Save or Submit button , set `force_regenerate: true` to trigger verification after form submission.
    
    ## Important - Junction Detection:
    **Case 1 - Failed step is a junction:**
    If the failed step above shows "IS JUNCTION", your recovery step MUST also include `is_junction: true` and the same `junction_info`.
    
        """
        #print(prompt)
        return prompt

    def evaluate_paths(
            self,
            completed_paths: List[Dict],
            discover_all_combinations: bool = False,
            max_paths: int = 7
    ) -> Dict:
        """
        Use AI to evaluate completed paths and determine next junction combination to test.

        Args:
            completed_paths: List of completed paths with full junction details
                [{"path_number": 1, "junctions": [{"name": "accountType", "chosen_option": "individual", "all_options": ["individual", "corporate"], "is_confirmed": True}, ...]}, ...]
            discover_all_combinations: If True, test ALL combinations. If False, just ensure each option tested once.
            max_paths: Maximum number of paths allowed

        Returns:
            {
                "all_paths_complete": bool,
                "next_path": {"junction_name": "option_to_select", ...},
                "total_paths_estimated": int,
                "reason": str,
                "tokens_used": int,
                "cost": float
            }
        """
        print(f"[AIHelper] Evaluating paths with AI...")
        logger.info(f"[AIHelper] AI path evaluation - {len(completed_paths)} completed paths")

        prompt = self._build_path_evaluation_prompt(
            completed_paths, discover_all_combinations, max_paths
        )

        try:
            response_text = self._call_api_with_retry(prompt, max_tokens=2000)

            if not response_text:
                logger.error("[AIHelper] No response from AI for path evaluation")
                return {
                    "all_paths_complete": True,
                    "next_path": {},
                    "total_paths_estimated": len(completed_paths),
                    "reason": "AI returned no response - defaulting to complete",
                    "tokens_used": 0,
                    "cost": 0
                }

            print(f"[AIHelper] Path evaluation response: {response_text[:500]}")

            # Strip markdown code blocks
            clean_response = response_text
            if '```json' in clean_response:
                clean_response = clean_response.split('```json')[1].split('```')[0]
            elif '```' in clean_response:
                clean_response = clean_response.split('```')[1].split('```')[0]

            # Parse JSON response
            result = json.loads(clean_response.strip())

            # Add token/cost estimates
            result["tokens_used"] = len(prompt) // 4 + len(response_text) // 4
            result["cost"] = result["tokens_used"] * 0.000003

            logger.info(
                f"[AIHelper] Path evaluation result: all_complete={result.get('all_paths_complete')}, next={result.get('next_path')}")
            return result

        except json.JSONDecodeError as e:
            logger.error(f"[AIHelper] Failed to parse path evaluation response: {e}")
            return {
                "all_paths_complete": True,
                "next_path": {},
                "total_paths_estimated": len(completed_paths),
                "reason": f"Failed to parse AI response: {e}",
                "tokens_used": 0,
                "cost": 0
            }
        except Exception as e:
            logger.error(f"[AIHelper] Path evaluation error: {e}")
            return {
                "all_paths_complete": True,
                "next_path": {},
                "total_paths_estimated": len(completed_paths),
                "reason": f"Error: {e}",
                "tokens_used": 0,
                "cost": 0
            }

    def _build_path_evaluation_prompt(
            self,
            completed_paths: List[Dict],
            discover_all_combinations: bool,
            max_paths: int
    ) -> str:
        """Build prompt for AI path evaluation."""

        # Format completed paths with full junction details
        paths_text = ""
        if not completed_paths:
            paths_text = "(No paths completed yet)\n"
        else:
            for path in completed_paths:
                path_num = path.get("path_number", "?")
                paths_text += f"\nPath {path_num}:\n"
                for junc in path.get("junctions", []):
                    name = junc.get("name", "unknown")
                    chosen = junc.get("chosen_option", "?")
                    all_opts = junc.get("all_options", [])
                    confirmed = junc.get("is_confirmed", False)
                    paths_text += f"  - {name}: chose '{chosen}' from options {all_opts} (confirmed={confirmed})\n"

        if discover_all_combinations:
            mode_instruction = """
    **MODE: DISCOVER ALL COMBINATIONS**
    Test ALL possible combinations of junction options.
    If junction B only appears when A=x, valid combinations are: (A=x, B=1), (A=x, B=2), (A=y) - not (A=y, B=1).
    """
        else:
            mode_instruction = """
    **MODE: ENSURE EACH OPTION TESTED ONCE**
    Test each junction option at least once to reach all form fields.
    You do NOT need all combinations - just ensure every option is tested ONCE globally.
    """

        prompt = f"""You are determining which form paths to test next.

    ## GOAL
    Test each junction option at least once. Once an option has been tested in ANY path, it is DONE - do not re-test it.

    ## YOUR TASK
    {mode_instruction}

    ## UNDERSTANDING THE DATA
    Each completed path shows ALL junctions that appeared during that form submission. If a junction is NOT listed in a path, it does NOT EXIST for that parent - do not try to add it. Some junctions only appear under specific parent values (nesting). If a path shows only a parent junction with no children, that parent has no child junctions.

    ## COMPLETED PATHS
    {paths_text}

    ## CONSTRAINTS
    - Current completed paths: {len(completed_paths)}

    ## RULES FOR BUILDING next_path
    
    1. **ONE CHANGE AT A TIME** - Change only ONE junction option per path. Keep all other junctions the same as the path that revealed them.
    2. **USE THE SAME PATH** - To test an untested option, use a path where that junction exists (just change that one option).
    3. Junction names may vary slightly ("A" vs "a" are the same).
    4. **ONLY INCLUDE SEEN JUNCTIONS** - Only include junctions you have SEEN exist together in a previous path. Don't assume a child junction will exist under a different option.
    5. **GLOBALLY TESTED = DONE** - If an option was already tested in a previous path, it is complete. Don't re-test it.
    6. ** CRITICAL - WE ARE NOT TESTING ALL COMBINATION. WE ARE JUST TESTING FOR EACH OF THE DIFFERENT JUNCTIONS EACH OF ITS OPTIONS

    ## EXAMPLE

    Completed paths:
    - Path 1: A='x' (A options: ['x', 'y']), B='1' (B options: ['1', '2']), C='red' (C options: ['red', 'blue'])

    CORRECT next_path: {{"A": "x", "B": "2"}}
    - ONE change: B from '1' to '2'
    - Keep A the same as Path 1
    - Do NOT include C - we haven't seen C exist under B='2'

    WRONG: {{"A": "x", "B": "2", "C": "red"}}
    - We haven't seen C under B='2' - don't assume it exists!

    WRONG: {{"A": "x", "B": "2", "C": "blue"}}
    - TWO problems: assuming C exists under B='2', AND two changes at once!

    WRONG: {{"A": "y", "B": "2"}}
    - B was only seen under A='x' - don't assume it exists under A='y'!

    CORRECT next_path (for new parent): {{"A": "y"}}
    - A='y' was never tested, so include ONLY A - the form will reveal what junctions exist under 'y'

    EXAMPLE FOR RULE 5 (GLOBALLY TESTED):
    Completed paths:
    - Path 1: A='x', B='1', C='red'
    - Path 2: A='x', B='2'
    - Path 3: A='x', B='1', C='blue'
    - Path 4: A='y'

    All options tested: A='x' (Path 1), A='y' (Path 4), B='1' (Path 1), B='2' (Path 2), C='red' (Path 1), C='blue' (Path 3).

    WRONG next_path: {{"A": "y", "C": "blue"}}
    - C='blue' was already tested globally in Path 3 - don't re-test under A='y'!

    CORRECT: All paths complete - all options were already covered.

    ## RESPONSE FORMAT
    Return ONLY valid JSON (no markdown):
    {{
        "all_paths_complete": true/false,
        "next_path": {{"junction_name": "option_to_select"}},
        "total_paths_estimated": <number>,
        "reason": "Brief explanation"
    }}

    If all paths are complete:
    {{
        "all_paths_complete": true,
        "next_path": {{}},
        "total_paths_estimated": {len(completed_paths)},
        "reason": "All junction options have been tested"
    }}
    """
        print(prompt)
        return prompt
