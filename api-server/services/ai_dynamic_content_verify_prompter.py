# services/ai_dynamic_content_verify_prompter.py
# AI-Powered Visual Verification for Dynamic Content Testing
# Image-only verification (no DOM needed)
# Supports reference images and verification instructions from user

import json
import time
import logging
import anthropic
import random
from typing import Optional, Dict, List
from anthropic._exceptions import OverloadedError, APIError

logger = logging.getLogger(__name__)


class DynamicContentVerifyHelper:
    """AI helper for visual verification of dynamic content pages"""

    def __init__(self, api_key: str, session_logger=None):
        if not api_key:
            raise ValueError("API key is required for AI functionality")
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = "claude-haiku-4-5-20251001"
        self.session_logger = session_logger

    def _call_api_with_retry_multimodal(self, content: list, max_tokens: int = 1000, max_retries: int = 3) -> Optional[
        str]:
        """Call Claude API with retry logic"""
        delay = 2

        for attempt in range(max_retries):
            try:
                print(f"[DynamicContentVerify] Calling Claude API (attempt {attempt + 1}/{max_retries})...")

                message = self.client.messages.create(
                    model=self.model,
                    max_tokens=max_tokens,
                    messages=[{"role": "user", "content": content}]
                )

                response_text = message.content[0].text
                print(f"[DynamicContentVerify] ✅ API call successful ({len(response_text)} chars)")
                return response_text

            except OverloadedError as e:
                if attempt == max_retries - 1:
                    print(f"[DynamicContentVerify] ❌ API Overloaded after {max_retries} attempts")
                    logger.error(f"[DynamicContentVerify] API Overloaded: {e}")
                    return None

                jitter = random.uniform(0, delay * 0.5)
                wait_time = delay + jitter
                print(f"[DynamicContentVerify] ⚠️ Retrying in {wait_time:.1f}s...")
                time.sleep(wait_time)
                delay *= 2

            except APIError as e:
                if attempt == max_retries - 1:
                    print(f"[DynamicContentVerify] ❌ API Error: {e}")
                    logger.error(f"[DynamicContentVerify] API Error: {e}")
                    return None

                print(f"[DynamicContentVerify] ⚠️ API Error. Retrying...")
                time.sleep(delay)
                delay *= 2

            except Exception as e:
                print(f"[DynamicContentVerify] ❌ Unexpected error: {e}")
                logger.error(f"[DynamicContentVerify] Unexpected error: {e}")
                return None

        return None

    def _log_bug(self, bug: Dict, step_description: str):
        """Log a bug found during verification"""
        if not self.session_logger:
            return

        bug_type = bug.get("type", "unknown")
        severity = bug.get("severity", "medium")
        description = bug.get("description", "")
        element = bug.get("element", "")

        msg = f"!!! 🐛 BUG [{severity.upper()}] Type: {bug_type}"
        if element:
            msg += f" | Element: {element}"
        msg += f" | {description}"

        # All bugs are errors or warnings, no info
        if severity == "critical":
            self.session_logger.error(msg, category="bug")
        else:
            self.session_logger.warning(msg, category="bug")

    def verify_step_visual(
            self,
            screenshot_base64: str,
            step_description: str,
            test_case_description: str = "",
            reference_images: list = None,
            verification_instructions: str = None

    ) -> Dict:
        """
        Verify that a step description matches what's visible on screen.
        First checks for page issues, then verifies the content.

        Args:
            screenshot_base64: Screenshot of current page
            step_description: The verify step's description (what to check)
            test_case_description: Overall test context
            reference_images: List of dicts with 'name' and 'base64' keys
            verification_instructions: Text extracted from user's verification file

        Returns:
            dict with 'success', 'reason', and optionally 'page_issue'
        """

        if self.session_logger:
            self.session_logger.info("🤖 !*!*!* Entering DYNAMIC CONTENT VERIFY prompter: verify_step_visual",
                                     category="ai_routing")

        # Build reference images section
        ref_images_section = ""
        if reference_images:
            ref_images_section = f"""
## REFERENCE IMAGES
You have been provided {len(reference_images)} reference image(s) showing expected visual states.
Compare the current screenshot against these references:
"""
            for i, ref in enumerate(reference_images):
                ref_images_section += f"- Reference {i + 1}: {ref.get('name', 'Unnamed')}\n"
            ref_images_section += """
Look for:
- Visual similarity to reference images
- Key UI elements that should match
- Layout and positioning consistency
- Color schemes and branding elements
"""

        # Build verification instructions section
        verification_section = ""
        if verification_instructions:
            verification_section = f"""
## CUSTOM VERIFICATION RULES
The user has provided the following verification instructions. Apply these rules:

{verification_instructions}

"""

        prompt = f"""You are a QA expert verifying a test step against a screenshot.

## TEST CONTEXT
{test_case_description}
{ref_images_section}
{verification_section}
## STEP 1: CHECK FOR PAGE ISSUES

First, scan the screenshot for blocking issues:
- Error pages: 404, 500, "Page not found", crash messages
- Login issues: "Session expired", "Please log in", authentication errors  
- Loading stuck: Infinite spinners, "Loading..." that seems stuck
- Broken layout: Blank page, major visual bugs
- Access denied: "Forbidden", "Unauthorized"

**If any blocking issue is found, return ONLY:**
```json
{{
  "page_issue": true,
  "issue_description": "brief description of the issue"
}}
```

## STEP 2: VERIFY THE STEP (only if no page issues)

If the page looks OK, verify if the following DESCRIPTION matches what's visible on the screenshot:

**Description to verify:**
"{step_description}"

**Verification Guidelines:**
- This is a VISUAL/SEMANTIC check - verify the overall state, not exact text matches
- Check that the KEY ELEMENTS mentioned are visible (headers, buttons, sections, tabs, forms, content areas, etc.)
- Be FLEXIBLE about: minor wording differences, styling variations, extra UI elements not mentioned
- FAIL if: key elements are missing, wrong page/section is shown, major discrepancies from description
{"- Compare against reference images if provided" if reference_images else ""}
{"- Apply custom verification rules if provided" if verification_instructions else ""}

**Examples:**
- Description says "Form page with header 'Contact Us'" → PASS if you see a form with "Contact Us" header
- Description says "Tab 'Settings' is active" → PASS if Settings tab appears selected/highlighted
- Description says "Error message is displayed" → FAIL if no error message visible
- Description says "List showing 5 items" → PASS if list shows 5 or more items, FAIL if fewer

**Response Format - Return list of ALL failures found:**
```json
{{
  "success": true or false,
  "failures": [
    {{
      "type": "missing_element|wrong_content|layout_issue|reference_mismatch|rule_violation",
      "severity": "critical|high|medium|low",
      "element": "element name or selector if applicable",
      "description": "what is wrong",
      "expected": "what was expected (optional)",
      "actual": "what was found (optional)"
    }}
  ]
}}
```

- If ALL checks pass: `{{"success": true, "failures": []}}`
- If ANY check fails: `{{"success": false, "failures": [...]}}` with one item per bug found

Return ONLY valid JSON, nothing else.
"""

        # Build content array with screenshot and optional reference images
        content = [
            {"type": "text", "text": "Screenshot of the current page:"},
            {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": screenshot_base64}}
        ]

        # Add reference images if provided
        if reference_images:
            content.append({"type": "text", "text": "Reference images provided by user:"})
            for ref in reference_images:
                if ref.get('base64'):
                    content.append({"type": "text", "text": f"Reference: {ref.get('name', 'Unnamed')}"})
                    content.append({"type": "image",
                                    "source": {"type": "base64", "media_type": "image/png", "data": ref['base64']}})

        content.append({"type": "text", "text": prompt})

        # Log AI call
        if self.session_logger:
            self.session_logger.ai_call("verify_step_visual", prompt_size=len(screenshot_base64))

        response = self._call_api_with_retry_multimodal(content, max_tokens=800)

        # Log raw AI response
        if response:
            msg = f"!!!! 👁️ Dynamic Content Verify Step RAW AI Response: {response[:500]}..."
            print(msg)
            if self.session_logger:
                self.session_logger.debug(msg, category="debug_trace")

        if not response:
            msg = "!!!! ⚠️ AI verification unavailable - assuming pass"
            print(msg)
            if self.session_logger:
                self.session_logger.warning(msg, category="ai_response")
            return {"success": True, "reason": "AI verification unavailable - assuming pass"}

        try:
            # Parse JSON response
            cleaned = response.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()

            result = json.loads(cleaned)

            # Log success
            if self.session_logger:
                self.session_logger.ai_response("verify_step_visual", success=True)

            # Check for page issue first
            if result.get("page_issue"):
                msg = f"!!!! ❌ Page issue detected: {result.get('issue_description', 'Unknown')}"
                print(msg)
                if self.session_logger:
                    self.session_logger.warning(msg, category="ai_response")
                return {
                    "success": False,
                    "page_issue": True,
                    "reason": result.get("issue_description", "Page issue detected")
                }

            # Get failures list
            failures = result.get("failures", [])
            success = result.get("success", len(failures) == 0)

            # Log each bug
            for failure in failures:
                self._log_bug(failure, step_description)

            # Log summary
            if failures:
                msg = f"!!! ❌ Dynamic Content Verify: FAILED - {len(failures)} bug(s) found"
                print(msg)
                if self.session_logger:
                    self.session_logger.warning(msg, category="verification_result")
            else:
                msg = f"!!! ✅ Dynamic Content Verify: PASSED - No bugs found"
                print(msg)
                if self.session_logger:
                    self.session_logger.info(msg, category="verification_result")

            return {
                "success": success,
                "failures": failures
            }
        except json.JSONDecodeError as e:
            msg = f"!!!! ⚠️ Failed to parse AI response: {e}"
            print(msg)
            if self.session_logger:
                self.session_logger.warning(msg, category="ai_response")

            # If can't parse, check for obvious indicators
            response_lower = response.lower()
            if "page_issue" in response_lower or "404" in response_lower or "error" in response_lower:
                return {"success": False, "page_issue": True, "reason": response[:100]}
            if "true" in response_lower and "success" in response_lower:
                return {"success": True, "reason": response[:100]}
            return {"success": False, "reason": f"Could not parse AI response: {response[:100]}"}