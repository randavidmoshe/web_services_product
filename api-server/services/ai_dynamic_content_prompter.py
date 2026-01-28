# services/ai_dynamic_content_prompter.py
# AI-Powered Step Generation for Dynamic Content Testing
# Simpler than form mapper - no junctions, no force_regenerate

import json
import time
import logging
import anthropic
import random
from typing import Dict, List, Optional, Any
from anthropic._exceptions import OverloadedError, APIError

logger = logging.getLogger(__name__)


class DynamicContentAIHelper:
    """AI helper for dynamic content testing - generates steps from natural language test cases"""

    def __init__(self, api_key: str, session_logger=None):
        if not api_key:
            raise ValueError("API key is required for AI functionality")
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = "claude-sonnet-4-5-20250929"
        self.session_logger = session_logger

    def _call_api_with_retry_multimodal(self, content: list, max_tokens: int = 8000, max_retries: int = 3) -> Optional[str]:
        """Call Claude API with retry logic for multimodal content"""
        delay = 2

        for attempt in range(max_retries):
            try:
                print(f"[DynamicContentAI] Calling Claude API (attempt {attempt + 1}/{max_retries})...")

                message = self.client.messages.create(
                    model=self.model,
                    max_tokens=max_tokens,
                    messages=[{"role": "user", "content": content}]
                )

                response_text = message.content[0].text
                print(f"[DynamicContentAI] ✅ API call successful ({len(response_text)} chars)")
                return response_text

            except OverloadedError as e:
                if attempt == max_retries - 1:
                    print(f"[DynamicContentAI] ❌ API Overloaded after {max_retries} attempts")
                    logger.error(f"[DynamicContentAI] API Overloaded: {e}")
                    return None

                jitter = random.uniform(0, delay * 0.5)
                wait_time = delay + jitter
                print(f"[DynamicContentAI] ⚠️ API Overloaded. Retrying in {wait_time:.1f}s...")
                time.sleep(wait_time)
                delay *= 2

            except APIError as e:
                if attempt == max_retries - 1:
                    print(f"[DynamicContentAI] ❌ API Error: {e}")
                    logger.error(f"[DynamicContentAI] API Error: {e}")
                    return None

                print(f"[DynamicContentAI] ⚠️ API Error. Retrying...")
                time.sleep(delay)
                delay *= 2

            except Exception as e:
                print(f"[DynamicContentAI] ❌ Unexpected error: {e}")
                logger.error(f"[DynamicContentAI] Unexpected error: {e}")
                return None

        return None

    def generate_test_steps(
            self,
            dom_html: str,
            screenshot_base64: Optional[str] = None,
            test_case_description: str = ""
    ) -> Dict[str, Any]:
        """
        Generate test steps from natural language test case description.

        Args:
            dom_html: Current page DOM
            screenshot_base64: Screenshot of current page
            test_case_description: Natural language test case (e.g., "Search for Python, verify results")

        Returns:
            Dict with 'steps' list
        """

        if self.session_logger:
            self.session_logger.info("🤖 !*!*!* Entering DYNAMIC CONTENT prompter: generate_test_steps", category="ai_routing")

        prompt = f"""You are a test automation expert. Generate Selenium WebDriver test steps based on the user's test case description.

## FIRST: CHECK FOR PAGE ISSUES

Scan DOM and screenshot for blocking issues:
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

**If NO page errors:** Continue below.

## TEST CASE DESCRIPTION
{test_case_description}

## CURRENT PAGE DOM
{dom_html}

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

**Modal buttons - use XPath for precision:**
- `//div[contains(@class, 'modal')]//button[contains(text(), 'Save')]`
- `//div[contains(@class, 'modal')]//button[@type='submit']`

**Class matching:** Use `contains(@class, 'x')` not `@class='x'`

**Rules:**
- Never use CSS `:contains()` or `:has()` - not supported in Selenium

**full_xpath field (MANDATORY FOR ALL ACTION STEPS):**
- Fallback selector if primary selector fails
- Must start from `/html/body/...`
- **USE IDs WHEN AVAILABLE:** If any element in the path has an ID, use it instead of counting:
  - ✅ `/html/body/div[@id='app']/div/form/input[1]`
  - ❌ `/html/body/div[3]/div/form/input[1]` (counting is error-prone)
- Only use indices `[n]` when no ID exists on that element

**CRITICAL - CLICK LOCATORS MUST INCLUDE ELEMENT TEXT/NAME:**
When generating selectors for click actions, ALWAYS include the element's visible text:
- ✅ `//button[contains(text(), 'Submit Order')]`
- ✅ `//a[text()='View Details']`
- ✅ `//span[contains(text(), 'Play')]/ancestor::button`
- ❌ `button.btn-primary` (too generic - will match wrong button during test runs)
- ❌ `.submit-btn` (no text - can't identify specific element)

This ensures the same logical element is found during test execution, even if page content changes.

## AVAILABLE ACTIONS

- **click**: Click an element
- **fill**: Type text into input field
- **select**: Select dropdown option
- **check/uncheck**: Checkbox actions
- **hover**: Hover over element
- **scroll**: Scroll page or element
- **wait**: Wait for condition (use sparingly)
- **verify**: Visual AI verification - describe what should be visible (no selector needed)

## RESPONSE FORMAT

Return ONLY valid JSON:
```json
{{
  "steps": [
    {{
      "step_number": 1,
      "action": "fill",
      "selector": "input[name='search']",
      "value": "Python",
      "description": "Enter search term",
      "field_name": "Search",
      "full_xpath": "/html/body/div[@id='app']//input[@name='search']"
    }},
    {{
      "step_number": 2,
      "action": "click",
      "selector": "//button[contains(text(), 'Search')]",
      "description": "Click search button",
      "field_name": "Search Button",
      "full_xpath": "/html/body/div[@id='app']//button[contains(text(), 'Search')]"
    }},
    {{
      "step_number": 3,
      "action": "verify",
      "description": "Search results page shows list of Python-related items"
    }}
  ]
}}
```

**field_name (REQUIRED for click and fill actions):**
- Use the EXACT label text visible on the page
- For buttons/clickables, use the button text
- For inputs, use the associated label text

## RULES

1. Generate steps that accomplish the test case description
2. Include verify steps when test case description asks for verification
3. Use robust selectors that won't break easily
4. Keep steps atomic - one action per step
5. Add wait steps only when necessary (after navigation, dynamic content)
6. Include full_xpath as fallback for CSS selectors

## SEARCH FIRST STRATEGY
When page has a search box, ALWAYS use it to find items:
- ✅ Search for "Movie Name" → click result
- ❌ Scroll through list hoping to find item
This makes steps more reliable and faster.

## VALUE PLACEHOLDERS FOR CREATE OPERATIONS
When creating new items (playlists, libraries, accounts, etc.), use placeholders:
- `{{RANDOM_NAME}}` — system replaces with random name during test run
- `{{RANDOM_EMAIL}}` — system generates random email
- `{{TIMESTAMP}}` — system inserts current timestamp

Example flow:
1. fill - name field - value: "{{RANDOM_NAME}}"
2. click - "//button[contains(text(), 'Create')]"
3. fill - search box - value: "{{RANDOM_NAME}}"  (find what we just created)
4. click - "//div[contains(text(), '{{RANDOM_NAME}}')]"

## FOLLOW USER'S TEST CASE STRICTLY
Generate ONLY what the test case description asks for.
Do NOT invent additional actions or verifications.
User may also provide a **reference image** — use it to understand the page.

## VERIFY STEPS — VISUAL AI VERIFICATION
Only generate verify steps when test case description asks to verify something.
Use visual descriptions of what should be visible.
**No selector needed for verify** — just describe what user asked to see.
**CONSOLIDATE verifications**: If verifying multiple things on the SAME page, put them ALL in ONE verify step.
- ❌ BAD: Step 2: verify "Form visible", Step 3: verify "Name field", Step 4: verify "Email field"
- ✅ GOOD: Step 2: verify "Form visible with Name and Email fields"


"""

        # Build multimodal content
        content = []

        if screenshot_base64:
            content.append({
                "type": "text",
                "text": "Screenshot of the current page:"
            })
            content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/png",
                    "data": screenshot_base64
                }
            })

        content.append({
            "type": "text",
            "text": prompt
        })

        response = self._call_api_with_retry_multimodal(content, max_tokens=8000)

        if not response:
            return {"steps": [], "error": "AI call failed"}

        # Parse response
        try:
            cleaned = response.strip()
            if "```json" in cleaned:
                cleaned = cleaned.split("```json")[1].split("```")[0]
            elif "```" in cleaned:
                cleaned = cleaned.split("```")[1].split("```")[0]

            result = json.loads(cleaned.strip())

            # Check if AI detected page errors
            if result.get("page_error_detected"):
                print(f"[DynamicContentAI] ⚠️ Page error detected: {result.get('error_type')}")
                return {
                    "steps": [],
                    "page_error_detected": True,
                    "error_type": result.get("error_type", "unknown")
                }

            steps = result.get("steps", [])

            print(f"[DynamicContentAI] Generated {len(steps)} steps")
            return {"steps": steps}

        except json.JSONDecodeError as e:
            logger.error(f"[DynamicContentAI] Failed to parse response: {e}")
            return {"steps": [], "error": f"Parse error: {e}"}

    def regenerate_remaining_steps(
            self,
            dom_html: str,
            executed_steps: List[Dict],
            test_case_description: str,
            screenshot_base64: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Regenerate remaining steps after some steps have been executed.
        """

        if self.session_logger:
            self.session_logger.info("🤖 !*!*!*! Entering DYNAMIC CONTENT prompter: regenerate_remaining_steps",
                                     category="ai_routing")

        executed_summary = "\n".join([
            f"Step {s.get('step_number', '?')}: {s.get('action')} - {s.get('description', '')}"
            for s in executed_steps
        ])

        prompt = f"""You are a test automation expert. Continue generating test steps for a partially completed test.

## FIRST: CHECK FOR PAGE ISSUES

Scan DOM and screenshot for blocking issues:
- "Page Not Found", "404", "Error", "Session Expired", "Access Denied", empty page
- "This site can't be reached", "refused to connect", "took too long to respond"

**If page error detected, return ONLY:**
```json
{{{{
  "page_error_detected": true,
  "error_type": "page_not_found"
}}}}
```

**If NO page errors:** Continue below.

## TEST CASE DESCRIPTION
{test_case_description}

## ALREADY EXECUTED STEPS
{executed_summary}

## CURRENT PAGE DOM (after executed steps)
{dom_html}

## YOUR TASK
Generate the REMAINING steps needed to complete the test case.
Do NOT repeat already executed steps.
Continue step numbering from {len(executed_steps) + 1}.

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

**Modal buttons - use XPath for precision:**
- `//div[contains(@class, 'modal')]//button[contains(text(), 'Save')]`
- `//div[contains(@class, 'modal')]//button[@type='submit']`

**Class matching:** Use `contains(@class, 'x')` not `@class='x'`

**Rules:**
- Never use CSS `:contains()` or `:has()` - not supported in Selenium

**full_xpath field (MANDATORY FOR ALL ACTION STEPS):**
- Fallback selector if primary selector fails
- Must start from `/html/body/...`
- **USE IDs WHEN AVAILABLE:** If any element in the path has an ID, use it instead of counting:
  - ✅ `/html/body/div[@id='app']/div/form/input[1]`
  - ❌ `/html/body/div[3]/div/form/input[1]` (counting is error-prone)
- Only use indices `[n]` when no ID exists on that element

**CRITICAL - CLICK LOCATORS MUST INCLUDE ELEMENT TEXT/NAME:**
When generating selectors for click actions, ALWAYS include the element's visible text:
- ✅ `//button[contains(text(), 'Submit Order')]`
- ✅ `//a[text()='View Details']`
- ✅ `//span[contains(text(), 'Play')]/ancestor::button`
- ❌ `button.btn-primary` (too generic - will match wrong button during test runs)
- ❌ `.submit-btn` (no text - can't identify specific element)

This ensures the same logical element is found during test execution, even if page content changes.

## AVAILABLE ACTIONS

- **click**: Click an element
- **fill**: Type text into input field
- **select**: Select dropdown option
- **check/uncheck**: Checkbox actions
- **hover**: Hover over element
- **scroll**: Scroll page or element
- **wait**: Wait for condition (use sparingly)
- **verify**: Visual AI verification - describe what should be visible (no selector needed)

## RESPONSE FORMAT

Return ONLY valid JSON:
```json
{{
  "steps": [
    {{
      "step_number": {len(executed_steps) + 1},
      "action": "fill",
      "selector": "input[name='search']",
      "value": "Python",
      "description": "Enter search term",
      "full_xpath": "//input[@name='search']"
    }},
    {{
      "step_number": {len(executed_steps) + 2},
      "action": "click",
      "selector": "//button[contains(text(), 'Search')]",
      "description": "Click search button",
      "full_xpath": "//button[contains(text(), 'Search')]"
    }},
    {{
      "step_number": {len(executed_steps) + 3},
      "action": "verify",
      "description": "Search results page shows list of Python-related items"
    }}
  ]
}}
```

## RULES

1. Generate steps that accomplish the test case description
2. Include verify steps when test case description asks for verification
3. Use robust selectors that won't break easily
4. Keep steps atomic - one action per step
5. Add wait steps only when necessary (after navigation, dynamic content)
6. Include full_xpath as fallback for CSS selectors

## SEARCH FIRST STRATEGY
When page has a search box, ALWAYS use it to find items:
- ✅ Search for "Movie Name" → click result
- ❌ Scroll through list hoping to find item
This makes steps more reliable and faster.

## VALUE PLACEHOLDERS FOR CREATE OPERATIONS
When creating new items (playlists, libraries, accounts, etc.), use placeholders:
- `{{RANDOM_NAME}}` — system replaces with random name during test run
- `{{RANDOM_EMAIL}}` — system generates random email
- `{{TIMESTAMP}}` — system inserts current timestamp

Example flow:
1. fill - name field - value: "{{RANDOM_NAME}}"
2. click - "//button[contains(text(), 'Create')]"
3. fill - search box - value: "{{RANDOM_NAME}}"  (find what we just created)
4. click - "//div[contains(text(), '{{RANDOM_NAME}}')]"

## FOLLOW USER'S TEST CASE STRICTLY
Generate ONLY what the test case description asks for.
Do NOT invent additional actions or verifications.
User may also provide a **reference image** — use it to understand the page.

## VERIFY STEPS — VISUAL AI VERIFICATION
Only generate verify steps when test case description asks to verify something.
Use visual descriptions of what should be visible.
**No selector needed for verify** — just describe what user asked to see.
**CONSOLIDATE verifications**: If verifying multiple things on the SAME page, put them ALL in ONE verify step.
**In the description put all the items that the test case asked to verify
- ❌ BAD: Step 2: verify "Form visible", Step 3: verify "Name field", Step 4: verify "Email field"
- ✅ GOOD: Step 2: verify "Form visible with Name and Email fields"


"""

        content = []

        if screenshot_base64:
            content.append({"type": "text", "text": "Current page screenshot:"})
            content.append({
                "type": "image",
                "source": {"type": "base64", "media_type": "image/png", "data": screenshot_base64}
            })

        content.append({"type": "text", "text": prompt})

        response = self._call_api_with_retry_multimodal(content, max_tokens=8000)

        if not response:
            return {"steps": []}

        try:
            cleaned = response.strip()
            if "```json" in cleaned:
                cleaned = cleaned.split("```json")[1].split("```")[0]
            elif "```" in cleaned:
                cleaned = cleaned.split("```")[1].split("```")[0]

            result = json.loads(cleaned.strip())

            # Check if AI detected page errors
            if result.get("page_error_detected"):
                print(f"[DynamicContentAI] ⚠️ Page error detected: {result.get('error_type')}")
                return {
                    "steps": [],
                    "page_error_detected": True,
                    "error_type": result.get("error_type", "unknown")
                }

            return {"steps": result.get("steps", [])}

        except json.JSONDecodeError as e:
            logger.error(f"[DynamicContentAI] Failed to parse regenerate response: {e}")
            return {"steps": []}

    def analyze_failure_and_recover(
            self,
            failed_step: Dict,
            executed_steps: List[Dict],
            fresh_dom: str,
            screenshot_base64: str,
            test_case_description: str,
            attempt_number: int = 1,
            error_message: str = ""
    ) -> List[Dict]:
        """
        Analyze a failed step and generate recovery steps.
        """

        if self.session_logger:
            self.session_logger.info("🤖 !*!*!* Entering DYNAMIC CONTENT prompter: analyze_failure_and_recover",
                                     category="ai_routing")

        prompt = f"""You are a test automation expert. A test step failed and needs recovery.

## STEP 1: CHECK FOR PAGE ISSUES

Scan DOM and screenshot for blocking issues:
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

**If NO page errors:** Continue below.

## STEP 2: CHECK FOR LOADING SPINNER

Look at screenshot for any rotating/spinning loading indicator that blocks interaction.

**If loading spinner is visible, return:**
```json
{{
  "recovery_steps": [
    {{"step_number": 1, "action": "wait_spinner_hidden", "selector": ".spinner-selector-from-dom", "value": "15", "description": "Wait for loading spinner to disappear", "full_xpath": ""}}
  ],
  "analysis": "Loading spinner detected"
}}
```
Find spinner in DOM by looking at screenshot. Common patterns: spinner, loader, loading, progress, busy, pending, processing, circular, overlay, backdrop, or SVG/icon animations.

**If no spinner visible:** Continue below.

---

## STEP 3: FIX THE FAILED STEP

🖼️ **Screenshot and DOM provided.** DOM is primary source, screenshot for visual verification.

**Task:** Fix the failed step. Return ONLY fix steps (1-3 max).

## Failed Step (Attempt {attempt_number}):
- Action: {failed_step.get('action')}
- Selector: {failed_step.get('selector')}
- Description: {failed_step.get('description')}
- Error: {error_message}

## TEST CASE DESCRIPTION
{test_case_description}

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
- ✅ GOOD - Scope to parent: `//div[@id='container']//button[text()='Save']`
- ✅ GOOD - Use index (CORRECT syntax): `(//button[@class='submit'])[1]` (parentheses FIRST, then index)
- ❌ WRONG index syntax: `//button[@class='submit'][1]` (index applies to child position, not result set)

**Stale element:**
- Page refreshed - add wait, retry same selector

**Wrong context:**
- Inside iframe → switch_to_frame first
- Need main page → switch_to_default first

## Selector Priority:
1. ID: `#fieldId`
2. Name: `[name='fieldName']`
3. Data attributes: `[data-testid='field']`
4. Scoped XPath: `//parent[@id='x']//child`

Use `contains(@class, 'x')` not `@class='x'` for partial class match.

## full_xpath - MANDATORY FOR ALL NON-VERIFY ACTIONS
For `verify` action recovery: use empty string `"full_xpath": ""`
For all other actions: full_xpath is CRITICAL as fallback since original selector FAILED.

**Rules:**
- Must start from `/html/body/...`
- **USE IDs WHEN AVAILABLE:** `/html/body/div[@id='app']/...` NOT `/html/body/div[1]/...`
- Only use indices `[n]` when no ID exists on that element
- Use `contains(@class, 'x')` for class matching

**SELF-VERIFICATION (MANDATORY):**
After constructing each full_xpath, trace it step-by-step through the DOM to verify:
1. Does the path start correctly from body?
2. Did you use IDs where available?
3. Did you count child indices correctly?
4. Does the final element match your target?

**❌ BAD full_xpath:**
`/html/body/div[1]/div/div[2]/div/div[1]/div/div[3]/div`
- All indices, ignores `id="app"` that exists in DOM!

**✅ GOOD full_xpath:**
`/html/body/div[@id='app']//div[contains(@class,'form')]//input[@name='email']`

## Response Format:
Return ONLY valid JSON:
```json
{{
  "recovery_steps": [
    {{
      "step_number": 1,
      "action": "click",
      "selector": "#trigger",
      "description": "Click trigger to open menu",
      "field_name": "Menu Trigger",
      "full_xpath": "/html/body/div[@id='app']/nav/button"
    }}
  ],
  "analysis": "Brief explanation of failure and fix"
}}
```
"""

        content = []

        if screenshot_base64:
            content.append({"type": "text", "text": "Current page screenshot:"})
            content.append({
                "type": "image",
                "source": {"type": "base64", "media_type": "image/png", "data": screenshot_base64}
            })

        content.append({"type": "text", "text": prompt})

        response = self._call_api_with_retry_multimodal(content, max_tokens=2000)

        if not response:
            return []

        try:
            cleaned = response.strip()
            if "```json" in cleaned:
                cleaned = cleaned.split("```json")[1].split("```")[0]
            elif "```" in cleaned:
                cleaned = cleaned.split("```")[1].split("```")[0]

            result = json.loads(cleaned.strip())

            # Check if AI detected page errors
            if result.get("page_error_detected"):
                print(f"[DynamicContentAI] ⚠️ Page error detected during recovery: {result.get('error_type')}")
                return []  # Return empty to signal failure

            recovery_steps = result.get("recovery_steps", [])
            print(f"[DynamicContentAI] Generated {len(recovery_steps)} recovery steps")
            return recovery_steps

        except json.JSONDecodeError as e:
            logger.error(f"[DynamicContentAI] Failed to parse recovery response: {e}")
            return []