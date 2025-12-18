# ai_form_mapper_main_prompter.py
# AI-Powered Test Step Generation using Claude API

import json
import time
import logging
import anthropic
import random
from typing import List, Dict, Optional, Any
from anthropic._exceptions import OverloadedError, APIError

logger = logging.getLogger('init_logger.form_page_test')
result_logger_gui = logging.getLogger('init_result_logger_gui.form_page_test')


class AIHelper:
    """Helper class for AI-powered step generation using Claude API"""
    
    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("API key is required for AI functionality")
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = "claude-sonnet-4-5-20250929"
    
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
                    return None
                
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
                    return None
                
                print(f"[AIHelper] ⚠️  API Error: {e}. Retrying in {delay}s... ({attempt + 1}/{max_retries})")
                logger.warning(f"[AIHelper] API Error. Retry {attempt + 1}/{max_retries} after {delay}s")
                
                time.sleep(delay)
                delay *= 2
                
            except Exception as e:
                print(f"[AIHelper] ❌ Unexpected error: {e}")
                logger.error(f"[AIHelper] Unexpected error: {e}")
                return None
        
        return None
    
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
                    return None
                
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
                    return None
                
                print(f"[AIHelper] ⚠️  API Error: {e}. Retrying in {delay}s... ({attempt + 1}/{max_retries})")
                logger.warning(f"[AIHelper] API Error. Retry {attempt + 1}/{max_retries} after {delay}s")
                
                time.sleep(delay)
                delay *= 2
                
            except Exception as e:
                print(f"[AIHelper] ❌ Unexpected error: {e}")
                logger.error(f"[AIHelper] Unexpected error: {e}")
                return None
        
        return None

    def generate_test_steps(
            self,
            dom_html: str,
            test_cases: List[Dict[str, str]],
            screenshot_base64: Optional[str] = None,
            critical_fields_checklist: Optional[Dict[str, str]] = None,
            field_requirements: Optional[str] = None,
            junction_instructions: Optional[str] = None,
            # Legacy params - kept for backward compatibility with callers
            previous_steps: Optional[List[Dict]] = None,
            step_where_dom_changed: Optional[int] = None,
            test_context=None,
            is_first_iteration: bool = False
    ) -> Dict[str, Any]:
        """
        Generate Selenium test steps based on DOM and test cases.

        Returns:
            Dict with 'steps' (list), 'ui_issue' (string), and 'no_more_paths' (bool)
        """

        # Build UI verification section - simplified intro without UI verification task
        ui_task_section = "You are a test automation expert. Your task is to generate Selenium WebDriver test steps for the form page.\n\n"
        
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
🔀 JUNCTION INSTRUCTIONS 🔀
{junction_instructions}
Follow these choices exactly.

"""

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
{screenshot_section}
{critical_fields_section}
{route_planning_section}
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
         
             
        **CRITICAL - AVOID GENERIC CLASS SELECTORS:**
        ❌ BAD: input.oxd-input.oxd-input--active (matches sidebar Search AND form fields!)
        ✅ GOOD: form .form-row input (scoped to form)
        ✅ GOOD: input[placeholder='Event Name'] (unique attribute)
        ✅ GOOD: //label[contains(text(),'Event Name')]/following::input[1] (XPath with label)
        
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
        
        **MANDATORY: FILL ALL FIELDS**
        ================================================================================
        **CRITICAL: You MUST fill EVERY field you encounter, regardless of whether it has a * (required) marker or not.**
        
        - Fill ALL text inputs
        - Fill ALL textareas
        - Select options in ALL dropdowns
        - Check ALL checkboxes (if applicable)
        - Fill ALL date/time fields
        - Upload files to ALL file upload fields
        - Fill ALL fields in ALL tabs/sections
        - Fill ALL fields in modals/popups
        - Fill ALL fields in iframes
        
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
          "description": "Create test resume PDF"
        }},
        {{
          "step_number": 16,
          "action": "upload_file",
          "selector": "input[name='resumeUpload']",
          "value": "test_resume.pdf",
          "description": "Upload resume file"
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
          "description": "Create test profile image"
        }},
        {{
          "step_number": 9,
          "action": "upload_file",
          "selector": "input[type='file'][name='profileImage']",
          "value": "profile_photo.png",
          "description": "Upload profile photo"
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
          "description": "Create test document PDF"
        }},
        {{
          "step_number": 23,
          "action": "upload_file",
          "selector": "input#documentUpload",
          "value": "test_document.pdf",
          "description": "Upload test document"
        }}
        ```
        
        **IMPORTANT Rules:**
        - ALWAYS create files with simple, relevant content (3-5 lines)
        - Use descriptive filenames that match the field purpose
        - The filename in create_file MUST match the value in upload_file
        - File content should be contextual (resume for resume field, invoice for invoice field, etc.)
        - Never skip file upload fields - treat them as MANDATORY
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
        
        **Junctions (dropdowns, radios, checkbox groups):**
        For fields with multiple options, add `"is_junction": true` and `"junction_info": {{"all_options": ["opt1", "opt2", ...], "chosen_option": "your_choice"}}`. Choose a non-default option.
               
        
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
        - ONLY the main identifying field (e.g., Person Name, Company Name, Title) gets a random suffix like "_184093" (e.g., "John Doe_184093")
        - ALL OTHER FIELDS should have NORMAL realistic values WITHOUT any suffix!
        
        - Name (main field): {'Add unique suffix (e.g., TestUser_184093)'}
        - Email: {'Normal email like john@example.com (NO suffix!)'}
        - Phone, Address, City, State, Zip, Country, Numbers: Normal realistic values (NO suffix!)
        - Dates: Look at screenshot/placeholder for required format

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
        - fill: Enter text in input field
        - clear: Clear input field before filling
        - select: Choose from dropdown OR select radio button
        - check: Check checkbox (only if not already checked)
        - uncheck: Uncheck checkbox (only if currently checked)
        - slider: Set range slider to percentage (value: 0-100)
        - drag_and_drop: Drag element to target (selector: source, value: target selector)
        - press_key: Send keyboard key (value: ENTER, TAB, ESCAPE, ARROW_DOWN, etc.)
        - verify: Check if element is visible
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
        
        **SLIDER ACTION:**
        For range sliders (like employment status slider):
        ```json
        {{"action": "slider", "selector": "input[type='range']#employmentStatus", "value": "50", "description": "Set employment status to 50% (Partially Employed)"}}
        ```
        Value must be 0-100 (percentage). Examples:
        - "0" = leftmost (Unemployed)
        - "50" = middle (Partially Employed) 
        - "100" = rightmost (Employed)
        
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
        {{"action": "fill", "selector": "input#fieldA", "value": "SomeValue"}},
        {{"action": "wait_for_ready", "selector": "input#fieldB", "description": "Wait for Field B to load via AJAX"}},
        {{"action": "fill", "selector": "input#fieldB", "value": "AnotherValue"}}
        ```

        **IMPORTANT: Use 'select' action for BOTH:**
        - <select> dropdowns: {{"action": "select", "selector": "select[name='country']", "value": "USA"}}
        - Radio buttons: {{"action": "select", "selector": "input[value='option1']", "value": "option1"}}


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
        
        2. **Verify the field** contains original value:
           - Action: "verify"
           - Selector: the field selector
           - Value: the EXPECTED ORIGINAL value from TEST_1 (the value that was filled in create test)
        
        3. **Clear the field** (for text inputs only):
           - Action: "clear"
           - Selector: the field selector
           - Skip this step for: select dropdowns, checkboxes, radio buttons, sliders
        
        4. **Update the field** with new value:
           - Action: "fill" or "select" or "check" (depending on field type)
           - Selector: the field selector
           - Value: the new updated value
        
        5. **Navigate back** (if needed):
           - Switch back from iframe: use switch_to_default
           - Switch back from shadow DOM: use switch_to_default
        
        **Example for field in iframe:**
        - switch_to_frame (navigate to iframe)
        - verify (check original value)
        - clear (clear the field)
        - fill (update with new value)
        - switch_to_default (exit iframe)
        
        **Example for field requiring hover:**
        - hover (reveal hidden field)
        - wait_for_visible (wait for field to appear)
        - verify (check original value)
        - clear (clear the field)
        - fill (update with new value)

        === OUTPUT REQUIREMENTS ===

        1. **Return ONLY valid JSON array** - no explanations, no markdown, just JSON

        2. **Each action must have these fields:**
           - "step_number": integer (sequential, starting from 1)
           - "test_case": string (which test this belongs to)
           - "action": string (navigate, click, fill, select, verify, etc.)
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

        4. **Verification Steps:**
           After important actions, verify success:
           - Do NOT generate more than 3-4 verify steps during form filling (TEST_1)
           - After navigation → verify new page/section loaded
           - After form completion → verify confirmation displayed

        5. **Wait Times:**
           - After navigate: 2 seconds
           - After click (page change): 2 seconds
           - After fill: 0.5 seconds
           - After verify: 1 second

        3. **Breaking Down Generic Steps:**
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
            "value": null,
            "verification": "form opens",
            "wait_seconds": 2
          }},
          {{
            "step_number": 2,
            "test_case": "Complete Form Following Random Path",
            "action": "fill",
            "description": "Enter name in form",
            "selector": "input[name='name']",
            "value": "TestUser123",
            "verification": null,
            "wait_seconds": 0.5
          }},
          {{
            "step_number": 3,
            "test_case": "Complete Form Following Random Path",
            "action": "click",
            "description": "Click address tab",
            "selector": "button[data-tab='address']",
            "value": null,
            "verification": null,
            "wait_seconds": 1
          }},
          {{
            "step_number": 4,
            "test_case": "Complete Form Following Random Path",
            "action": "switch_to_frame",
            "description": "Access address iframe",
            "selector": "iframe#address-frame",
            "value": null,
            "verification": null,
            "wait_seconds": 1
          }},
          {{
            "step_number": 5,
            "test_case": "Complete Form Following Random Path",
            "action": "fill",
            "description": "Fill street address",
            "selector": "input[name='street']",
            "value": "123 Main St",
            "verification": null,
            "wait_seconds": 0.5
          }},
          {{
            "step_number": 6,
            "test_case": "Complete Form Following Random Path",
            "action": "switch_to_default",
            "description": "Return to main page",
            "selector": null,
            "value": null,
            "verification": null,
            "wait_seconds": 0.5
          }},
          {{
            "step_number": 7,
            "test_case": "Complete Form Following Random Path",
            "action": "fill",
            "description": "Fill Field A (triggers AJAX)",
            "selector": "input#fieldA",
            "value": "SampleValue",
            "verification": null,
            "wait_seconds": 0.5
          }},
          {{
            "step_number": 8,
            "test_case": "Complete Form Following Random Path",
            "action": "wait_for_ready",
            "description": "Wait for Field B to load via AJAX",
            "selector": "input#fieldB",
            "value": null,
            "verification": null,
            "wait_seconds": 0
          }},
          {{
            "step_number": 9,
            "test_case": "Complete Form Following Random Path",
            "action": "fill",
            "description": "Fill Field B",
            "selector": "input#fieldB",
            "value": "DependentValue",
            "verification": null,
            "wait_seconds": 0.5
          }},
          {{
            "step_number": 9,
            "test_case": "Complete Form Following Random Path",
            "action": "click",
            "description": "Click the Add button to add a new finding item",
            "selector": "button.btn-add-finding",
            "value": null,
            "verification": null,
            "wait_seconds": 0.5
          }},
          {{
            "step_number": 10,
            "test_case": "Complete Form Following Random Path",
            "action": "select",
            "description": "Select inquiry type (random choice)",
            "selector": "select[name='inquiry_type']",
            "value": "General",
            "verification": null,
            "wait_seconds": 0.5
          }},
          {{
            "step_number": 8,
            "test_case": "Complete Form Following Random Path",
            "action": "click",
            "description": "Click submit button",
            "selector": "button[type='submit']",
            "value": null,
            "verification": "form submitted",
            "wait_seconds": 2
          }},
          {{
            "step_number": 9,
            "test_case": "Complete Form Following Random Path",
            "action": "wait_for_hidden",
            "description": "Wait for success message to disappear",
            "selector": ".success-message",
            "value": null,
            "verification": "success message disappeared",
            "wait_seconds": 1
          }}
        ]


        === FINAL CHECKLIST BEFORE RESPONDING ===

        Before you output your JSON, verify:
        ☐ NO :has-text() selectors anywhere
        ☐ NO :contains() selectors anywhere  
        ☐ NO :text() selectors anywhere
        ☐ For VERIFY actions: selector finds element by location, expected value goes in value field
        ☐ ALL selectors use attributes, IDs, classes, or structure
        ☐ Each generic step expanded into specific actions
        ☐ Following ONE path through the form
        ☐ Valid JSON format (no trailing commas, proper quotes)

        === RESPONSE FORMAT ===
        Return ONLY a JSON object with this structure:
        ```json
        {{
          "steps": [
            {{"step_number": 1, "action": "fill", "selector": "input#field", "value": "value", "description": "Fill field", "full_xpath": "/html/body/div[1]/form/input", "force_regenerate": false}},
            {{"step_number": 2, "action": "click", "selector": "button.submit", "description": "Submit form", "full_xpath": "/html/body/div[1]/form/button", "force_regenerate": true}}
          ],
          "no_more_paths": false
        }}
        ```
        
        **full_xpath field (MANDATORY FOR ALL STEPS, BUT NOT for verify action):**
        - Fallback selector if primary selector fails
        - Must start from `/html/body/...`
        - **COUNTING IS CRITICAL:** Count ALL direct children of each parent, including hidden elements, modals, overlays
        - Double-check your count
        - **USE IDs WHEN AVAILABLE:** If any element in the path has an ID, use it instead of counting:
          - ✅ `/html/body/div[@id='findingModal']/div/div[4]/button[2]`
          - ❌ `/html/body/div[3]/div/div[4]/button[2]` (counting is error-prone)
        - Only use indices `[n]` when no ID exists on that element
        - Trace the path carefully from body → target element using the DOM
        - For `verify` action: use empty string `""`
        
        **force_regenerate field (REQUIRED):**
        - Set to `true` for steps that change page context: Save, Submit, Edit, View, Delete,  etc.
        - Set to `false` for regular interactions: fill, select, click tab, check, hover, next, continue, etc.
        - This tells the system to regenerate steps after this action completes

        - **steps**: Array of step objects to execute
        - **no_more_paths**: Set to `true` ONLY if all junction combinations have been explored (no new paths possible). Otherwise `false`.

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
                    no_more_paths = result.get("no_more_paths", False)
                    
                    logger.info(f"[AIHelper] Successfully parsed {len(steps)} steps")
                    print(f"[AIHelper] Successfully parsed {len(steps)} steps")
                    if no_more_paths:
                        print(f"[AIHelper] 🏁 AI indicates no more paths to explore")
                    
                    return {"steps": steps, "ui_issue": "", "no_more_paths": no_more_paths}
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
                print(f"[AIHelper] Response text: {response_text[:500]}")
                return {"steps": [], "ui_issue": "", "no_more_paths": False}
            
        except Exception as e:
            result_logger_gui.error(f"[AIHelper] Error: {e}")
            print(f"[AIHelper] Error: {e}")
            import traceback
            traceback.print_exc()
            return {"steps": [], "ui_issue": "", "no_more_paths": False}

    def regenerate_steps(
            self,
            dom_html: str,
            executed_steps: list,
            test_cases: list,
            test_context,
            screenshot_base64: Optional[str] = None,
            critical_fields_checklist: Optional[Dict[str, str]] = None,
            field_requirements: Optional[str] = None,
            junction_instructions: Optional[str] = None
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
        try:
            print(f"[AIHelper] Regenerating steps after DOM change...")
            print(f"[AIHelper] Already executed: {len(executed_steps)} steps")

            # Build context of what's been done
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
🔀 JUNCTION INSTRUCTIONS:
{junction_instructions}

"""

            # Screenshot section
            screenshot_section = ""
            if screenshot_base64:
                screenshot_section = """
🖼️ CRITICAL - FILL ALL FIELDS (DO NOT SKIP ANY) BY VIEWING THE SCREENSHOT AND EXAMINING THE DOM:
1. Extract ALL input fields and repeatable lists with "Add"/"+"/etc from DOM (input, select, textarea, checkbox, radio, list items(with add buttons), everything user can add/input)
2. CHECK SCREENSHOT TO VIEW PAGE AND SEE ALL THE FIELDS AND LIST ITEMS - MUST NOT SKIP ANY FIELD
3. Generate steps for EVERY field and list item - do NOT skip any - first all fields in current tab then next tabs
4. Screenshot shows active tab/section and visual layout
5. BEFORE adding any navigation step (next tab, submit), re-check DOM and screenshot to ensure no field was skipped

"""

            # ==================== BUILD THE PROMPT ====================

            prompt = f"""You are a web automation expert generating Selenium WebDriver test steps.

{screenshot_section}{critical_fields_section}{route_planning_section}
## Current Context:

{executed_context}

## Current Page DOM:
{dom_html}

{test_cases_context}

## Your Task:
Generate the REMAINING steps to complete the test. Include 2-4 steps from next test case to ensure continuity.

**⚠️ DO NOT RE-FILL ALREADY COMPLETED FIELDS:**
- Check "Steps Already Completed" above - these fields are DONE
- NEVER generate fill/select/check steps for fields that already appear in completed steps
- Even if you see empty fields in DOM, if they were filled in completed steps, SKIP them

**Priority order:**
1. **CHECK CURRENT PAGE FIRST:** Look at DOM/screenshot - if you see a list/table, you're on list page. If you see read-only values, you're on detail page. Do NOT generate navigation to a page you're already on.
2. If previous step was next/continue button AND you see a blocking overlay...
3. Complete current tab 100% before moving to next tab:
   - Fill ALL input fields (text, date, email, etc.)
   - Click EVERY "Add" button you find (each is a DIFFERENT list - Advertisements, Affiliates , Items, etc.)
   - Handle special inputs (dropdowns, checkboxes, sliders, file uploads)
4. Only after ALL fields AND ALL "Add" buttons in current tab are done, navigate to next tab
5. Submit form and verify success

**For edit/update tests:** Navigate → Verify original value → Clear → Update → Navigate back

## Response Format:
```json
{{
  "steps": [
    {{"step_number": N, "action": "action", "selector": "selector", "value": "value", "description": "description", "full_xpath": "/html/body/.../element", "force_regenerate": false}}
  ],
  "no_more_paths": false
}}
```

**full_xpath field (MANDATORY FOR ALL STEPS, BUT NOT for verify action):**
- Fallback selector if primary selector fails
- Must start from `/html/body/...`
- **COUNTING IS CRITICAL:** Count ALL direct children of each parent, including hidden elements, modals, overlays
- Double-check your count
- **USE IDs WHEN AVAILABLE:** If any element in the path has an ID, use it instead of counting:
  - ✅ `/html/body/div[@id='findingModal']/div/div[4]/button[2]`
  - ❌ `/html/body/div[3]/div/div[4]/button[2]` (counting is error-prone)
- Only use indices `[n]` when no ID exists on that element
- Trace the path carefully from body → target element using the DOM
- For `verify` action: use empty string `""`

**force_regenerate field (REQUIRED):**
- Set to `true` for navigation actions: Edit, View, Next, Continue, Delete, Back to List buttons
- Set to `false` for: fill, select, click tab, check, hover, verify, scroll, ALL wait actions, switch_to_frame, switch_to_default

**force_regenerate_verify field (for Save/Submit only):**
- Set to `true` ONLY for Save and Submit buttons
- This triggers verification-focused AI after form submission

---

## Action Reference:

**Available actions:** fill, clear, select, click, double_click, check, uncheck, slider, drag_and_drop, press_key, verify, wait, wait_for_ready, wait_for_visible, wait_message_hidden, wait_spinner_hidden, scroll, hover, refresh, switch_to_frame, switch_to_default, switch_to_shadow_root, switch_to_window, switch_to_parent_window, create_file, upload_file

**Context switching:**
- `switch_to_frame` / `switch_to_shadow_root`: Enter iframe or shadow DOM
- `switch_to_default`: Exit from iframe OR shadow DOM back to main page (ALWAYS use this to return)
- `switch_to_parent_window`: Switch between browser windows/tabs only (NOT for iframe/shadow DOM)

**wait_message_hidden:** ONLY after page-level navigation (Next Page, Submit Form) when blocking overlay covers >30% of page. Do NOT use for success toasts or floating messages.

**wait_spinner_hidden:** ONLY when blocking spinner/loader covers >30% of page. Provide selector from DOM.

**Selection elements - choose correct action:**
- `select` → ONLY for `<select>` dropdowns
- `click` → For radio buttons, custom dropdowns, toggle buttons  
- `check`/`uncheck` → For checkboxes

**Slider:** value = 0-100 (percentage)
```json
{{"action": "slider", "selector": "input[type='range']", "value": "50", "description": "Set slider to 50%"}}
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

**Junctions:** Mark fields with multiple options
```json
{{"action": "select", "selector": "select#type", "value": "enterprise", "is_junction": true, "junction_info": {{"all_options": ["personal", "business", "enterprise"], "chosen_option": "enterprise"}}, "description": "Select type"}}
```

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

**Modal buttons - use XPath for precision:**
- `//div[contains(@class, 'modal')]//button[contains(text(), 'Save')]`
- `//div[contains(@class, 'modal')]//button[@type='submit']`

**Class matching:** Use `contains(@class, 'x')` not `@class='x'`


---
## VERIFICATION RULES

**⚠️ CRITICAL - VIEW/DETAIL PAGE ≠ FORM PAGE:**
After clicking View/Edit/Details button, you are on a READ-ONLY display page:
- ❌ WRONG: `input#fieldName`, `select#type`, `textarea#notes` (FORM elements - won't exist!)
- ✅ RIGHT: Data is displayed in `<span>`, `<div>`, `<td>`, `<dd>`, `<p>` - CHECK THE DOM!
- ALWAYS examine the CURRENT DOM structure before generating verify selectors

**VERIFY ALL FIELDS ON VIEW/DETAIL PAGES:**
When on a view/detail page, verify ALL fields that were filled during TEST_1:
1. Look through "Steps Already Completed" for ALL FILL/SELECT steps
2. Generate a VERIFY step for EACH field found - count them and verify count matches
3. Get expected values from the `value` field of those FILL/SELECT steps
4. Skip ONLY system-generated fields (timestamps, IDs, "Created At", "Updated At")

**⚠️ VERIFY ALL FIELDS ON EACH PAGE - NO SKIPPING:**
- On LIST page: verify fields visible in the table
- On VIEW page: verify ALL fields again, even if some were verified on list page
- Each page is independent - do NOT skip fields because they were verified on a previous page
- Person Name, Email, Phone etc. must be verified on BOTH list AND view pages

**⚠️ COMMON FIELDS OFTEN MISSED - DO NOT SKIP:**
- Date of Birth / Date fields
- Phone numbers
- Checkboxes (Newsletter, Terms)
- File upload filenames
- Dropdown selections

**How verify works:** Selector finds element by LOCATION. The `value` field contains expected text.

**BUILD SELECTOR FROM THE DOM - Common patterns:**
- By data attribute: `//div[@data-field='email']`
- By class: `(//div[contains(@class, 'field-value')])[1]` - use ACTUAL class from DOM
- By label proximity: `//label[contains(text(), 'Email')]/../div`
- Table structure: `//tr[contains(., 'Email')]//td[2]`

**❌ WRONG:**
- `//div[contains(text(), 'john@email.com')]` - expected value in selector!
- `input#email` on view page - form elements don't exist on view pages!
- Inventing class names not in DOM

**Class matching:** Use `contains(@class, 'x')` not `@class='x'`

---

## Rules:
- Never use CSS `:contains()` or `:has()` - not supported in Selenium
- Never use `wait` with value > 10 seconds - use wait_for_ready instead
- Fill ALL fields including optional ones
- Complete current tab before moving to next

Return ONLY the JSON object.
"""

            # Call Claude API with retry (with or without screenshot)
            result_logger_gui.info("[AIHelper] Sending regeneration request to Claude API...")

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
                #print(prompt_no_dom)
                #print("!" * 80 + "\n")
                #print("!*!*!*!*!*!*!*! Entering the AI func for Regenerate steps")
                response_text = self._call_api_with_retry_multimodal(message_content, max_tokens=16000,
                                                                     max_retries=3)
            else:
                response_text = self._call_api_with_retry(prompt, max_tokens=16000, max_retries=3)

            if response_text is None:
                print("[AIHelper] ❌ Failed to regenerate steps after retries")
                return {"steps": [], "ui_issue": "", "no_more_paths": False}

            print(f"[AIHelper] Received regeneration response ({len(response_text)} chars)")

            # Parse JSON response
            import re
            json_match = re.search(r'\{[\s\S]*\}', response_text)

            if json_match:
                response_data = json.loads(json_match.group())
                steps = response_data.get("steps", [])
                no_more_paths = response_data.get("no_more_paths", False)

                print(f"[AIHelper] Successfully regenerated {len(steps)} new steps")
                if no_more_paths:
                    print(f"[AIHelper] 🏁 AI indicates no more paths to explore")

                return {"steps": steps, "ui_issue": "", "no_more_paths": no_more_paths}
            else:
                print("[AIHelper] No JSON object found in regeneration response")
                return {"steps": [], "ui_issue": "", "no_more_paths": False}

        except Exception as e:
            print(f"[AIHelper] Error regenerating steps: {e}")
            import traceback
            traceback.print_exc()
            return {"steps": [], "ui_issue": "", "no_more_paths": False}

    def regenerate_verify_steps(
            self,
            dom_html: str,
            executed_steps: list,
            test_cases: list,
            test_context,
            screenshot_base64: Optional[str] = None,
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
"""

            # ==================== BUILD THE VERIFICATION PROMPT ====================

            prompt = f"""You are a web automation expert generating Selenium WebDriver VERIFICATION test steps.

## VERIFICATION MODE - AFTER SAVE/SUBMIT

You are now in VERIFICATION MODE. The form has been saved/submitted successfully.
Your task is to VERIFY that all entered data is displayed correctly.

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
2. For EACH field that was filled, generate a VERIFY step to confirm the value is displayed
3. If data is on a different page (e.g., need to click "View" button), add navigation steps
4. Verify ALL fields on EACH page you visit - do NOT skip fields even if verified on a previous page

**Current page detection:**
- If you see a LIST/TABLE page: Verify visible columns, then click View to see details
- If you see a VIEW/DETAIL page: Verify ALL fields displayed on this page
- If you see a SUCCESS message: Look for "View" or "Back to List" button to navigate

## Response Format:
```json
{{
  "steps": [
    {{"step_number": N, "action": "action", "selector": "selector", "value": "value", "description": "description", "full_xpath": "xpath", "force_regenerate": false}}
  ],
  "no_more_paths": false
}}
```

---

## VERIFICATION RULES

**⚠️ CRITICAL - VIEW/DETAIL PAGE ≠ FORM PAGE:**
After clicking View/Edit/Details button, you are on a READ-ONLY display page:
- ❌ WRONG: `input#fieldName`, `select#type`, `textarea#notes` (FORM elements - won't exist!)
- ✅ RIGHT: Data is displayed in `<span>`, `<div>`, `<td>`, `<dd>`, `<p>` - CHECK THE DOM!
- ALWAYS examine the CURRENT DOM structure before generating verify selectors

**VERIFY ALL FIELDS - NO SKIPPING:**
1. Look through "Steps Already Completed" for ALL fill/select/check steps
2. Generate a VERIFY step for EACH field - do NOT skip any
3. Each page requires FULL verification - do NOT skip fields verified on a previous page
4. Get expected values from the `value` field of those fill/select steps
5. Skip ONLY system-generated fields (timestamps, IDs, "Created At", "Updated At", "Saved Date")

**⚠️ CRITICAL - WHERE TO GET EXPECTED VALUES:**
- ✅ Get expected value from the `value` field in "Steps Already Completed" (what was ENTERED)
- ❌ NEVER use values from the current DOM (what is DISPLAYED) as expected values
- The whole point of verification is to CHECK if what was entered matches what is displayed
- Example: If fill step had `"value": "15-1-1990"`, verify with `"value": "15-1-1990"` - NOT what DOM shows

**How verify works:** Selector finds element by LOCATION. The `value` field contains expected text.

**BUILD SELECTOR FROM THE DOM - Common patterns:**
- By data attribute: `//div[@data-field='email']`
- By class: `(//div[contains(@class, 'field-value')])[1]` - use ACTUAL class from DOM
- By label proximity: `//label[contains(text(), 'Email')]/../div`
- By parent with label: `//div[@class='field-group'][.//div[@class='field-label'][contains(text(), 'Email')]]//div[@class='field-value']`
- Table structure: `//tr[contains(., 'Email')]//td[2]`

**❌ WRONG selectors:**
- `//div[contains(text(), 'john@email.com')]` - expected value in selector!
- `input#email` on view page - form elements don't exist on view pages!
- Inventing class names not in DOM

**Class matching:** Use `contains(@class, 'x')` not `@class='x'`

---

## Navigation Rules (for accessing view pages):

**Available actions:** click, verify, wait, wait_for_ready, wait_for_visible, wait_message_hidden, wait_spinner_hidden, scroll, hover, switch_to_frame, switch_to_default

**Selector preference order:**
1. ID: `#buttonId` or `button#viewBtn`
2. Data attributes: `[data-testid='view-button']`
3. Unique class: `button.view-btn`
4. XPath with attributes: `//button[@onclick='viewForm(0)']`
5. XPath by text: `//button[contains(text(), 'View')]`

**Modal buttons - use XPath for precision:**
- `//div[contains(@class, 'modal')]//button[contains(text(), 'View')]`

**force_regenerate_verify field (stay in verification mode):**
- Set to `true` for navigation within verification different pages: View button, Back to List (to verify list columns)
- Set to `false` for verify steps and wait steps

**force_regenerate field (exit verification mode):**
- Set to `true` ONLY when ALL verification is complete and ALL verification pages are complete AND next test case requires Edit/Update
- Use this to transition from verification to the next test case (e.g., Edit test)

**How to decide:**
1. If more fields to verify on another page → use `force_regenerate_verify: true`
2. If ALL fields verified and all Verification pages are done AND next test is Edit/Update → use `force_regenerate: true` on Edit button
3. If ALL fields verified AND no more tests → set `no_more_paths: true`


**full_xpath field:**
- Required for click/navigation steps - fallback selector starting from `/html/body/...`
- Prefer `[@id='...']` over index when element has an ID
- For `verify` action: use empty string `""`

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
                response_text = self._call_api_with_retry_multimodal(message_content, max_tokens=16000,
                                                                     max_retries=3)
            else:
                response_text = self._call_api_with_retry(prompt, max_tokens=16000, max_retries=3)

            if response_text is None:
                print("[AIHelper] ❌ Failed to regenerate verify steps after retries")
                return {"steps": [], "ui_issue": "", "no_more_paths": False}

            print(f"[AIHelper] Received verify regeneration response ({len(response_text)} chars)")

            # Parse JSON response
            import re
            json_match = re.search(r'\{[\s\S]*\}', response_text)

            if json_match:
                response_data = json.loads(json_match.group())
                steps = response_data.get("steps", [])
                no_more_paths = response_data.get("no_more_paths", False)

                print(f"[AIHelper] Successfully regenerated {len(steps)} verify steps")
                if no_more_paths:
                    print(f"[AIHelper] 🏁 AI indicates no more paths to explore")

                return {"steps": steps, "ui_issue": "", "no_more_paths": no_more_paths}
            else:
                print("[AIHelper] No JSON object found in verify regeneration response")
                return {"steps": [], "ui_issue": "", "no_more_paths": False}

        except Exception as e:
            print(f"[AIHelper] Error regenerating verify steps: {e}")
            import traceback
            traceback.print_exc()
            return {"steps": [], "ui_issue": "", "no_more_paths": False}

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
            response_text = self._call_api_with_retry_multimodal(content, max_tokens=16000, max_retries=3)
            #print(f"[DEBUG] Raw AI response: {response_text[:500]}...")
            
            if response_text is None:
                print("[AIHelper] ❌ Failed to get recovery response after retries")
                logger.error("[AIHelper] Failed to get recovery response after retries")
                return []
            
            print(f"[AIHelper] Received recovery response ({len(response_text)} chars)")
            logger.info(f"[AIHelper] Received recovery response ({len(response_text)} chars)")
            
            # Extract JSON from response
            json_match = re.search(r'\[[\s\S]*\]', response_text)
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

    🖼️ **Screenshot and DOM provided.** DOM is primary source, screenshot for visual verification.

    **Task:** Fix the failed step. Return ONLY fix steps (1-5 max). Do NOT generate remaining form steps.

    ## Failed Step (Attempt {attempt_number}/2):
    - Action: {action}
    - Selector: {selector}  
    - Description: {description}
    - Error: {error_message}
    {executed_context}
    {failure_history_section}
    ## Current DOM:
    ```html
    {fresh_dom}
    ```

    ---

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
    - Scope to parent: `//div[@id='container']//button[text()='Save']`
    - Use index: `(//button[@class='submit'])[1]`

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
      {{"step_number": 1, "action": "hover", "selector": "#trigger", "value": "", "description": "Re-hover to open menu"}},
      {{"step_number": 2, "action": "fill", "selector": "#field", "value": "test", "description": "Fill field in now-visible menu"}}
    ]
    ```
    """
        return prompt


