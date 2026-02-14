# services/ai_login_mapper_prompter.py
# AI helper for login/logout mapping - generates steps via orchestrator
# Follows same pattern as ai_dynamic_content_prompter.py:
#   generate_test_steps, regenerate_remaining_steps, analyze_failure_and_recover

import json
import time
import random
import logging
from typing import Dict, List, Optional, Any

import anthropic
from anthropic._exceptions import OverloadedError, APIError

logger = logging.getLogger(__name__)


class LoginMapperAIHelper:
    """AI helper for mapping login and logout flows via the orchestrator."""

    def __init__(self, api_key: str, session_logger=None):
        if not api_key:
            raise ValueError("API key is required for AI functionality")
        self.client = anthropic.Anthropic(api_key=api_key)
        #self.model = "claude-sonnet-4-5-20250929"
        self.model = "claude-haiku-4-5-20251001"
        self.session_logger = session_logger

    # ================================================================
    # API CALL HELPER
    # ================================================================

    def _call_api_with_retry_multimodal(
        self, content: list, max_tokens: int = 4000, max_retries: int = 3
    ) -> Optional[str]:
        """Call Claude API with retry logic for multimodal content."""
        delay = 2

        for attempt in range(max_retries):
            try:
                print(f"[LoginMapperAI] Calling Claude API (attempt {attempt + 1}/{max_retries})...")

                message = self.client.messages.create(
                    model=self.model,
                    max_tokens=max_tokens,
                    messages=[{"role": "user", "content": content}]
                )

                response_text = message.content[0].text
                print(f"[LoginMapperAI] ✅ API call successful ({len(response_text)} chars)")
                return response_text

            except OverloadedError:
                if attempt == max_retries - 1:
                    print(f"[LoginMapperAI] ❌ API Overloaded after {max_retries} attempts")
                    return None
                jitter = random.uniform(0, delay * 0.5)
                wait_time = delay + jitter
                print(f"[LoginMapperAI] ⚠️ API Overloaded. Retrying in {wait_time:.1f}s...")
                time.sleep(wait_time)
                delay *= 2

            except APIError as e:
                if attempt == max_retries - 1:
                    print(f"[LoginMapperAI] ❌ API Error: {e}")
                    logger.error(f"[LoginMapperAI] API Error: {e}")
                    return None
                print(f"[LoginMapperAI] ⚠️ API Error. Retrying...")
                time.sleep(delay)
                delay *= 2

            except Exception as e:
                print(f"[LoginMapperAI] ❌ Unexpected error: {e}")
                logger.error(f"[LoginMapperAI] Unexpected error: {e}")
                return None

        return None

    def _parse_response(self, response: str) -> Dict[str, Any]:
        """Parse JSON from AI response."""
        cleaned = response.strip()
        if "```json" in cleaned:
            cleaned = cleaned.split("```json")[1].split("```")[0]
        elif "```" in cleaned:
            cleaned = cleaned.split("```")[1].split("```")[0]
        return json.loads(cleaned.strip())

    # ================================================================
    # SHARED SELECTOR RULES (used in all prompts)
    # ================================================================

    SELECTOR_RULES = """## Selector Rules:

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
- ✅ `//button[contains(text(), 'Submit')]`
- ✅ `//a[text()='Sign In']`
- ❌ `button.btn-primary` (too generic)
- ❌ `.submit-btn` (no text)
"""

    # ================================================================
    # GENERATE INITIAL STEPS
    # ================================================================

    def generate_test_steps(
        self,
        dom_html: str,
        screenshot_base64: Optional[str] = None,
        login_credentials: Optional[Dict[str, str]] = None,
        mode: str = "login"
    ) -> Dict[str, Any]:
        """
        Generate login or logout automation steps.

        Args:
            dom_html: Current page DOM
            screenshot_base64: Screenshot of current page
            login_credentials: {"username": "...", "password": "..."} (login mode only)
            mode: "login" or "logout"

        Returns:
            Dict with 'steps' list
        """
        if self.session_logger:
            self.session_logger.info(
                f"🤖 !*!*!* Entering LOGIN MAPPER prompter: generate_test_steps (mode={mode})",
                category="ai_routing"
            )

        if mode == "login":
            prompt = self._build_login_prompt(dom_html, login_credentials or {})
        else:
            prompt = self._build_logout_prompt(dom_html, (login_credentials or {}).get("login_hints", ""))

        content = self._build_multimodal_content(prompt, screenshot_base64)
        response = self._call_api_with_retry_multimodal(content, max_tokens=4000)

        if not response:
            if self.session_logger:
                self.session_logger.error("!!!!! AI raw response: None (call failed)", category="ai_response")
            return {"steps": [], "error": "AI call failed"}

        try:
            result = self._parse_response(response)

            if result.get("page_error_detected"):
                print(f"[LoginMapperAI] ⚠️ Page error detected: {result.get('error_type')}")
                if self.session_logger:
                    self.session_logger.error(f"!!!! AI raw response (page_error): {response}",
                                              category="ai_response")
                return {
                    "steps": [],
                    "page_error_detected": True,
                    "error_type": result.get("error_type", "unknown")
                }

            if result.get("login_failed"):
                print(f"[LoginMapperAI] ❌ Login failed: {result.get('error_message')}")
                if self.session_logger:
                    self.session_logger.error(f"!!!!!!! AI raw response (login_failed): {response}",
                                              category="ai_response")
                return {
                    "steps": [],
                    "login_failed": True,
                    "error_message": result.get("error_message", "Login failed")
                }

            if result.get("already_logged_in"):
                print(f"[LoginMapperAI] Already logged in - no steps needed")
                return {
                    "steps": [],
                    "already_logged_in": True
                }

            steps = result.get("steps", [])
            print(f"[LoginMapperAI] Generated {len(steps)} {mode} steps")
            if not steps and self.session_logger:
                self.session_logger.error(f"!!!!!! AI raw response (0 steps): {response}", category="ai_response")
            return {"steps": steps}


        except json.JSONDecodeError as e:

            logger.error(f"[LoginMapperAI] Failed to parse response: {e}")

            if self.session_logger:
                self.session_logger.error(f"!!!!! AI raw response (parse_error): {response}", category="ai_response")

            return {"steps": [], "error": f"Parse error: {e}"}

    # ================================================================
    # REGENERATE REMAINING STEPS
    # ================================================================

    def regenerate_remaining_steps(
        self,
        dom_html: str,
        executed_steps: List[Dict],
        screenshot_base64: Optional[str] = None,
        login_credentials: Optional[Dict[str, str]] = None,
        mode: str = "login"
    ) -> Dict[str, Any]:
        """
        Regenerate remaining steps after DOM changed (e.g., 2FA page appeared).
        """
        if self.session_logger:
            self.session_logger.info(
                f"🤖 !*!*!* Entering LOGIN MAPPER prompter: regenerate_remaining_steps (mode={mode})",
                category="ai_routing"
            )

        executed_summary = "\n".join([
            f"Step {s.get('step_number', '?')}: {s.get('action')} - {s.get('description', '')}"
            for s in executed_steps
        ])

        if mode == "login":
            prompt = self._build_login_regenerate_prompt(
                dom_html, executed_summary, len(executed_steps), login_credentials or {}
            )
        else:
            prompt = self._build_logout_regenerate_prompt(
                dom_html, executed_summary, len(executed_steps), (login_credentials or {}).get("login_hints", "")
            )

        content = self._build_multimodal_content(prompt, screenshot_base64)
        response = self._call_api_with_retry_multimodal(content, max_tokens=4000)

        if not response:
            if self.session_logger:
                self.session_logger.error("!!!! AI raw response: None (call failed)", category="ai_response")
            return {"steps": []}

        try:
            result = self._parse_response(response)

            if result.get("page_error_detected"):
                print(f"[LoginMapperAI] ⚠️ Page error detected: {result.get('error_type')}")
                if self.session_logger:
                    self.session_logger.error(f"!!!! AI raw response (page_error): {response}",
                                              category="ai_response")
                return {
                    "steps": [],
                    "page_error_detected": True,
                    "error_type": result.get("error_type", "unknown")
                }

            if result.get("login_failed"):
                print(f"[LoginMapperAI] ❌ Login failed: {result.get('error_message')}")
                if self.session_logger:
                    self.session_logger.error(f"!!!! AI raw response (login_failed): {response}",
                                              category="ai_response")
                return {
                    "steps": [],
                    "login_failed": True,
                    "error_message": result.get("error_message", "Login failed")
                }

            if result.get("validation_errors_detected"):
                print(f"[LoginMapperAI] ⚠️ Validation errors detected: {result.get('explanation', '')}")
                if self.session_logger:
                    self.session_logger.error(f"!!!! AI raw response (validation_errors): {response}",
                                              category="ai_response")
                return {
                    "steps": [],
                    "validation_errors_detected": True,
                    "explanation": result.get("explanation", "")
                }

            steps = result.get("steps", [])
            if not steps and self.session_logger:
                self.session_logger.error(f"!!!!! AI raw response (0 steps): {response}", category="ai_response")
            return {"steps": steps}


        except json.JSONDecodeError as e:

            logger.error(f"[LoginMapperAI] Failed to parse regenerate response: {e}")

            if self.session_logger:
                self.session_logger.error(f"!!!!!AI raw response (parse_error): {response}", category="ai_response")

            return {"steps": []}

    # ================================================================
    # FAILURE RECOVERY
    # ================================================================

    def analyze_failure_and_recover(
        self,
        failed_step: Dict,
        executed_steps: List[Dict],
        fresh_dom: str,
        screenshot_base64: str,
        mode: str = "login",
        attempt_number: int = 1,
        error_message: str = ""
    ) -> List[Dict]:
        """Analyze a failed step and generate recovery steps."""

        if self.session_logger:
            self.session_logger.info(
                f"🤖 !*!*!* Entering LOGIN MAPPER prompter: analyze_failure_and_recover (mode={mode})",
                category="ai_routing"
            )

        context_label = "login" if mode == "login" else "logout"

        prompt = f"""You are a test automation expert. A {context_label} step failed and needs recovery.

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

**If no spinner visible:** Continue below.

---

## STEP 3: FIX THE FAILED STEP

**Task:** Fix the failed {context_label} step. Return ONLY fix steps (1-3 max).

## Failed Step (Attempt {attempt_number}):
- Action: {failed_step.get('action')}
- Selector: {failed_step.get('selector')}
- Description: {failed_step.get('description')}
- Error: {error_message}

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
- ✅ GOOD: `//div[@id='container']//button[text()='Save']`
- ✅ GOOD: `(//button[@class='submit'])[1]`
- ❌ WRONG: `//button[@class='submit'][1]`

{self.SELECTOR_RULES}

## Response Format:
Return ONLY valid JSON:
```json
{{
  "recovery_steps": [
    {{
      "step_number": 1,
      "action": "click",
      "selector": "#trigger",
      "description": "Click trigger to expand",
      "field_name": "Menu Trigger",
      "full_xpath": "/html/body/div[@id='app']/nav/button"
    }}
  ],
  "analysis": "Brief explanation of failure and fix"
}}
```
"""
        content = self._build_multimodal_content(prompt, screenshot_base64)
        response = self._call_api_with_retry_multimodal(content, max_tokens=2000)

        if not response:
            if self.session_logger:
                self.session_logger.error("AI raw response: None (call failed)", category="ai_response")
            return []

        try:
            result = self._parse_response(response)

            if result.get("page_error_detected"):
                print(f"[LoginMapperAI] ⚠️ Page error detected during recovery: {result.get('error_type')}")
                if self.session_logger:
                    self.session_logger.error(f"!!!!! AI raw response (page_error recovery): {response}",
                                              category="ai_response")
                return []

            recovery_steps = result.get("recovery_steps", [])
            print(f"[LoginMapperAI] Generated {len(recovery_steps)} recovery steps")
            return recovery_steps


        except json.JSONDecodeError as e:

            logger.error(f"[LoginMapperAI] Failed to parse recovery response: {e}")

            if self.session_logger:
                self.session_logger.error(f"!!!! AI raw response (parse_error recovery): {response}",
                                          category="ai_response")

            return []

    # ================================================================
    # PROMPT BUILDERS
    # ================================================================

    def _build_login_prompt(self, dom_html: str, credentials: Dict[str, str]) -> str:
        username = credentials.get("username", "")
        password = credentials.get("password", "")
        login_hints = credentials.get("login_hints", "")
        hints_section = f"## AI GUIDANCE NOTES FROM USER\n{login_hints}\n\n" if login_hints else ""

        return f"""You are a test automation expert. Your task is to log into a web application.

{hints_section}## FIRST: CHECK FOR PAGE ISSUES

**IMPORTANT — HTTP Basic Auth Detection:**
If the page appears blank/empty AND the AI Guidance Notes above mention "Basic Auth", "server auth", "HTTP auth", or "server authentication" — this is HTTP Basic Auth.
Selenium cannot interact with native auth dialogs.
Do NOT return page_error_detected.
Instead return ONLY:

```json
{{{{
  "steps": [
    {{{{
      "step_number": 1,
      "action": "navigate",
      "selector": "",
      "value": "",
      "is_basic_auth": true,
      "description": "Navigate with HTTP Basic Auth credentials",
      "force_regenerate": true
    }}}},
    {{{{
      "step_number": 2,
      "action": "wait",
      "selector": "body",
      "value": "",
      "description": "Wait for page to load after Basic Auth"
    }}}}
  ]
}}}}
```
Do NOT put any credentials in the URL — the system will inject them server-side.

**If none of the above apply, continue below.**

Scan DOM and screenshot for blocking issues:
- "Page Not Found", "404", "Error", "Session Expired", "Access Denied"
- "This site can't be reached", "refused to connect", "took too long to respond"
- "ERR_CONNECTION_REFUSED", "ERR_NAME_NOT_RESOLVED", "DNS_PROBE_FINISHED_NXDOMAIN"

**If page error detected, return ONLY:**
```json
{{{{
  "page_error_detected": true,
  "error_type": "page_not_found"
}}}}
```

**If the page appears to be a dashboard/home page (already logged in), return ONLY:**
```json
{{{{
  "already_logged_in": true
}}}}
```

**If NO issues:** Continue below.

## TASK: LOG IN TO THIS APPLICATION

Analyze the screenshot and DOM. Generate steps to complete the login process.

**Credentials:**
- Username/Email: `{username}`
- Password: `{password}`

## LOADING SPINNER HANDLING

If after analyzing the page you see a loading spinner/indicator, generate a `wait_spinner_hidden` step with `"force_regenerate": true` before the final wait step. Find the spinner element in the DOM (common patterns: spinner, loader, loading, progress, busy, overlay, circular, SVG animations).

## CAPTCHA DETECTION

If the page shows a CAPTCHA/reCAPTCHA challenge, return ONLY:
```json
{{{{
  "login_failed": true,
  "error_message": "CAPTCHA challenge detected - cannot automate"
}}}}
```

## LOGIN ERROR DETECTION

If the page already shows a login error message (from a previous attempt or stale session):
- "Invalid credentials", "Wrong password", "Incorrect username or password"
- "Login failed", "Authentication failed", "Account locked"
- "Too many attempts", "Account disabled", "User not found"
- Any red/orange banner, toast, or inline error near the login form

**If login error message detected, return ONLY:**
```json
{{{{
  "login_failed": true,
  "error_message": "The exact error text shown on the page"
}}}}
```

## IMPORTANT RULES

1. Look at the DOM and screenshot to understand what type of login page this is
2. Generate the steps needed - this could be a simple username/password form, or could involve multiple steps
3. You MUST use the exact credentials provided above in the `value` field of fill actions
4. After clicking the login/submit button, your LAST step must be a `wait` action for an element that confirms you reached the dashboard/home page (e.g., sidebar navigation, user avatar, main menu)

## 2FA / TOTP HANDLING

If the login page shows a TOTP/2FA/MFA verification code input field:
- Generate a `fill` action for it with `"value": ""` (empty - system will inject the code)
- Mark the step with `"is_totp": true`
- Then generate the submit/verify click step
- Then the final `wait` step for dashboard element

If this is a standard login page (no 2FA visible yet), just generate the normal login steps. If 2FA appears after login submission, the system will regenerate steps for the new page.

## CURRENT PAGE DOM
{dom_html}



{self.SELECTOR_RULES}

## AVAILABLE ACTIONS

- **fill**: Type text into input field (use for username, password, TOTP code)
- **click**: Click a button/link (use for login/submit button)
- **wait**: Wait for an element to appear (REQUIRED as last step - wait for dashboard element)
- **wait_spinner_hidden**: Wait for a loading spinner/overlay to disappear. Provide spinner selector from DOM.
- **wait_for_hidden**: Wait for an element to disappear (max 10s)
- **navigate**: Navigate to a URL (use for HTTP Basic Auth)
- **hover**: Hover over element (if needed to reveal menu)
- **scroll**: Scroll to element (if login form is below the fold)

## RESPONSE FORMAT

Return ONLY valid JSON:
```json
{{{{
  "steps": [
    {{{{
      "step_number": 1,
      "action": "fill",
      "selector": "#username",
      "value": "{username}",
      "description": "Enter username",
      "field_name": "Username",
      "full_xpath": "/html/body/div[@id='app']//input[@name='username']",
      "dont_regenerate": true
    }}}},
    {{{{
      "step_number": 2,
      "action": "fill",
      "selector": "#password",
      "value": "{password}",
      "description": "Enter password",
      "field_name": "Password",
      "full_xpath": "/html/body/div[@id='app']//input[@type='password']",
      "dont_regenerate": true
    }}}},
    {{{{
      "step_number": 3,
      "action": "click",
      "selector": "//button[contains(text(), 'Sign In')]",
      "description": "Click login button",
      "field_name": "Sign In",
      "full_xpath": "/html/body/div[@id='app']//button[@type='submit']",
      "force_regenerate": true,
      "dont_regenerate": false
    }}}},
    {{{{
      "step_number": 4,
      "action": "wait",
      "selector": ".dashboard-sidebar",
      "value": "15",
      "description": "Wait for dashboard to load after login",
      "field_name": "Dashboard",
      "full_xpath": "/html/body/div[@id='app']//nav[contains(@class,'sidebar')]",
      "dont_regenerate": true
    }}}}
  ]
}}}}
```
```

**field_name (REQUIRED for all action steps):**
- Use the EXACT label text visible on the page for inputs
- Use the button text for click actions
- Use the element name for wait actions

## RULES

1. Your steps must complete the login process visible on this page
2. Use the EXACT credentials provided above
3. Your LAST step MUST be a `wait` action for a dashboard/post-login element
4. Keep steps atomic - one action per step
5. Include full_xpath as fallback for every action step
6. Do NOT add unnecessary steps - just what's needed to log in
7. The click step that submits the login form (or any form like 2FA) MUST include `"force_regenerate": true` — this tells the system to re-analyze the page after clicking
8. **dont_regenerate field (REQUIRED):**
   - Set to `true` for: fill actions, wait actions, hover, scroll
   - Set to `false` for: click actions that submit a form (login button, verify button, 2FA submit)
   - This tells the system NOT to re-analyze the page after this step
"""

    def _build_logout_prompt(self, dom_html: str, login_hints: str = "") -> str:
        hints_section = f"## AI GUIDANCE NOTES FROM USER\n{login_hints}\n\n" if login_hints else ""
        return f"""You are a test automation expert. Your task is to log out of a web application.

{hints_section}## FIRST: CHECK FOR PAGE ISSUES

Scan DOM and screenshot for blocking issues:
- "Page Not Found", "404", "Error", "Session Expired", "Access Denied", empty page

**If page error detected, return ONLY:**
```json
{{{{
  "page_error_detected": true,
  "error_type": "page_not_found"
}}}}
```

**If the page already shows a login form (already logged out), return ONLY:**
```json
{{{{
  "already_logged_in": false
}}}}
```

**If NO issues:** Continue below.

## TASK: LOG OUT OF THIS APPLICATION

Analyze the screenshot and DOM. Generate steps to complete the logout process.

Common logout patterns:
- User avatar/name in header → click → dropdown with "Logout" option
- Direct "Logout" or "Sign Out" link in navigation
- Settings/gear icon → menu with logout option
- Sidebar menu with logout at the bottom

## CURRENT PAGE DOM
{dom_html}

{self.SELECTOR_RULES}

## AVAILABLE ACTIONS

- **click**: Click a button/link (use for menu triggers, logout buttons)
- **wait**: Wait for an element to appear (REQUIRED as last step - wait for login page element)
- **wait_spinner_hidden**: Wait for a loading spinner/overlay to disappear. Provide spinner selector from DOM.
- **wait_for_hidden**: Wait for an element to disappear (max 10s)
- **hover**: Hover over element (if needed to reveal logout option)

## RESPONSE FORMAT

Return ONLY valid JSON:
```json
{{
  "steps": [
    {{
      "step_number": 1,
      "action": "click",
      "selector": ".user-dropdown-trigger",
      "description": "Click user menu to open dropdown",
      "field_name": "User Menu",
      "full_xpath": "/html/body/div[@id='app']//div[contains(@class,'user-dropdown')]"
    }},
    {{
      "step_number": 2,
      "action": "click",
      "selector": "//a[contains(text(), 'Logout')]",
      "description": "Click logout option",
      "field_name": "Logout",
      "full_xpath": "/html/body/div[@id='app']//a[contains(text(),'Logout')]"
    }},
    {{
      "step_number": 3,
      "action": "wait",
      "selector": "input[name='username']",
      "value": "15",
      "description": "Wait for login page to confirm logout succeeded",
      "field_name": "Login Page",
      "full_xpath": "/html/body//input[@name='username']"
    }}
  ]
}}
```

## RULES

1. Your steps must complete the logout process
2. Your LAST step MUST be a `wait` action for a login page element (username field, password field, or login button) with a SPECIFIC CSS/XPath selector from the DOM
3. Keep steps atomic - one action per step
4. Include full_xpath as fallback for every action step
5. If logout requires opening a dropdown menu first, include that step
6. ONLY use actions from the AVAILABLE ACTIONS list above. Do NOT invent custom actions like "verify_login_page" or "check_logout" — use `wait` with a real selector instead
"""

    def _build_login_regenerate_prompt(
        self, dom_html: str, executed_summary: str,
        executed_count: int, credentials: Dict[str, str]
    ) -> str:
        username = credentials.get("username", "")
        password = credentials.get("password", "")
        login_hints = credentials.get("login_hints", "")
        hints_section = f"## AI GUIDANCE NOTES FROM USER\n{login_hints}\n\n" if login_hints else ""

        return f"""You are a test automation expert. Continue generating login steps for a partially completed login process.

{hints_section}## FIRST: CHECK FOR PAGE ISSUES

Scan DOM and screenshot for blocking issues:
- "Page Not Found", "404", "Error", "Session Expired", "Access Denied"

**If page error detected, return ONLY:**
```json
{{{{
  "page_error_detected": true,
  "error_type": "page_not_found"
}}}}
```

**If NO page errors:** Continue below.

## SECOND: CHECK FOR 2FA/TOTP ERRORS

If the current page is a TOTP/2FA/MFA verification page (code input fields visible) AND there is any error message on the page — "Invalid code", "Code expired", "Connection error", server error, or ANY other error — this is NOT a login failure. The system will retry with a fresh code.

**Return ONLY:**
```json
{{{{
  "validation_errors_detected": true,
  "explanation": "The exact error text shown on the 2FA page"
}}}}
```
**If NO 2FA/TOTP errors:** Continue below.

## THIRD: CHECK FOR LOGIN ERROR MESSAGES

Look at the DOM and screenshot for red/colored error messages indicating login failure:
- "Invalid credentials", "Wrong password", "Incorrect username or password"
- "Login failed", "Authentication failed", "Account locked"
- "Too many attempts", "Account disabled", "User not found"
- Any red/orange banner, toast, or inline error near the login form

**If login error message detected, return ONLY:**
```json
{{{{
  "login_failed": true,
  "error_message": "The exact error text shown on the page"
}}}}
```

**If NO login errors:** Continue below.

## FOURTH: CHECK FOR LOADING SPINNER

Look at the screenshot for any rotating/spinning loading indicator.

**If loading spinner is visible, return:**
```json
{{
  "steps": [
    {{
      "step_number": {executed_count + 1},
      "action": "wait_spinner_hidden",
      "selector": ".spinner-selector-from-dom",
      "value": "15",
      "description": "Wait for loading spinner to disappear",
      "field_name": "Loading Spinner",
      "full_xpath": "",
      "force_regenerate": true
    }}
  ]
}}
```
Find the spinner element in the DOM. Common patterns: spinner, loader, loading, progress, busy, overlay, circular, or SVG animations.

**If no spinner visible:** Continue below.

## FIFTH: CHECK IF LOGIN FORM IS STILL VISIBLE (nothing happened)

If the login form is still showing (username/password fields, login button still present) and there is NO spinner and NO error message, it means the login button click had no effect.

**If login form still visible with no changes, return ONLY:**
```json
{{{{
  "login_failed": true,
  "error_message": "Login button click had no effect - form still visible with no error or loading indicator"
}}}}
```

**If CAPTCHA/reCAPTCHA challenge appeared, return ONLY:**
```json
{{{{
  "login_failed": true,
  "error_message": "CAPTCHA challenge detected - cannot automate"
}}}}
```

**If account verification/locked message appeared, return ONLY:**
```json
{{{{
  "login_failed": true,
  "error_message": "The exact message shown on the page (e.g. Verify your email, Account locked)"
}}}}
```

**If none of the above:** Continue below.

## CREDENTIALS
- Username/Email: `{username}`
- Password: `{password}`

## ALREADY EXECUTED STEPS
{executed_summary}

## CURRENT PAGE DOM (after executed steps)
{dom_html}

## YOUR TASK

The page changed after executing the steps above. Generate the REMAINING steps to complete login.
Do NOT repeat already executed steps.
Continue step numbering from {executed_count + 1}.

Common scenarios for regeneration:
- **2FA/TOTP page appeared**: Generate fill step for TOTP code input with `"value": ""` and `"is_totp": true`, then submit click, then wait for dashboard
- **Additional verification page**: Generate steps to complete verification
- **Dashboard loaded**: Generate just the final `wait` step for a dashboard element

## 2FA / TOTP HANDLING
If the current page shows a TOTP/2FA/MFA code input field:
- Generate a `fill` action for it with `"value": ""` (empty - system will inject the code)
- Mark the step with `"is_totp": true`
- Then submit/verify click
- Then final `wait` for dashboard element

## IMPORTANT
- Your LAST step MUST be a `wait` action for a dashboard/post-login element
- If dashboard is already visible, just return the `wait` step

{self.SELECTOR_RULES}

## AVAILABLE ACTIONS
- **fill**: Type text into input field
- **click**: Click a button/link
- **wait**: Wait for element (REQUIRED as last step)
- **wait_spinner_hidden**: Wait for a loading spinner/overlay to disappear. Provide spinner selector from DOM.
- **wait_for_hidden**: Wait for an element to disappear (max 10s)
- **navigate**: Navigate to a URL
- **hover**: Hover over element
- **scroll**: Scroll to element

## RESPONSE FORMAT
Return ONLY valid JSON:
```json
{{
  "steps": [
    {{
      "step_number": {executed_count + 1},
      "action": "fill",
      "selector": "#totp-code",
      "value": "",
      "is_totp": true,
      "description": "Enter 2FA verification code",
      "field_name": "Verification Code",
      "full_xpath": "/html/body//input[@name='totp']",
      "dont_regenerate": true
    }},
    {{
      "step_number": {executed_count + 2},
      "action": "click",
      "selector": "//button[contains(text(), 'Verify')]",
      "description": "Click verify button",
      "field_name": "Verify",
      "full_xpath": "//button[@type='submit']",
      "force_regenerate": true,
      "dont_regenerate": false
    }},
    {{
      "step_number": {executed_count + 3},
      "action": "wait",
      "selector": ".dashboard-content",
      "value": "15",
      "description": "Wait for dashboard after verification",
      "field_name": "Dashboard",
      "full_xpath": "/html/body/div[@id='app']//div[contains(@class,'dashboard')]",
      "dont_regenerate": true
    }}
  ]
}}
```

**dont_regenerate field (REQUIRED):**
- Set to `true` for: fill actions, wait actions, hover, scroll
- Set to `false` for: click actions that submit a form (verify button, 2FA submit)
- This tells the system NOT to re-analyze the page after this step

"""

    def _build_logout_regenerate_prompt(
            self, dom_html: str, executed_summary: str, executed_count: int, login_hints: str = ""
    ) -> str:
        hints_section = f"## AI GUIDANCE NOTES FROM USER\n{login_hints}\n\n" if login_hints else ""
        return f"""You are a test automation expert. Continue generating logout steps.

{hints_section}## FIRST: CHECK FOR PAGE ISSUES

Scan DOM and screenshot for blocking issues.

**If page error detected, return ONLY:**
```json
{{{{
  "page_error_detected": true,
  "error_type": "page_not_found"
}}}}
```

**If NO page errors:** Continue below.

## ALREADY EXECUTED STEPS
{executed_summary}

## CURRENT PAGE DOM (after executed steps)
{dom_html}

## YOUR TASK

Generate the REMAINING steps to complete logout.
Continue step numbering from {executed_count + 1}.

- Your LAST step MUST be a `wait` for a login page element with a SPECIFIC CSS/XPath selector (e.g., `input[name='username']`)
- If login page is already visible, just return the `wait` step
- ONLY use actions from the AVAILABLE ACTIONS list below. Do NOT invent custom actions like "verify_login_page" or "check_logout" — use `wait` with a real selector instead

{self.SELECTOR_RULES}

## AVAILABLE ACTIONS
- **click**: Click a button/link
- **wait**: Wait for element (REQUIRED as last step)
- **wait_spinner_hidden**: Wait for a loading spinner/overlay to disappear. Provide spinner selector from DOM.
- **wait_for_hidden**: Wait for an element to disappear (max 10s)
- **hover**: Hover over element

## RESPONSE FORMAT
Return ONLY valid JSON:
```json
{{
  "steps": [
    {{
      "step_number": {executed_count + 1},
      "action": "click",
      "selector": "//a[contains(text(), 'Logout')]",
      "description": "Click logout",
      "field_name": "Logout",
      "full_xpath": "//a[contains(text(),'Logout')]"
    }},
    {{
      "step_number": {executed_count + 2},
      "action": "wait",
      "selector": "input[name='username']",
      "value": "15",
      "description": "Wait for login page",
      "field_name": "Login Page",
      "full_xpath": "//input[@name='username']"
    }}
  ]
}}
```
"""

    # ================================================================
    # MULTIMODAL CONTENT BUILDER
    # ================================================================

    def _build_multimodal_content(
        self, prompt: str, screenshot_base64: Optional[str] = None
    ) -> list:
        """Build multimodal content array for Claude API."""
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

        return content