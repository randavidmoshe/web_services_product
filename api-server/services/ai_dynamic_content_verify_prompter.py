# services/ai_dynamic_content_verify_prompter.py
# AI-Powered Visual Verification for Dynamic Content Testing
# Image-only verification (no DOM needed)

import json
import time
import logging
import anthropic
import random
from typing import Optional, Dict
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

    def verify_step_visual(
            self,
            screenshot_base64: str,
            step_description: str,
            test_case_description: str = ""
    ) -> Dict:
        """
        Verify that a step description matches what's visible on screen.
        First checks for page issues, then verifies the content.

        Args:
            screenshot_base64: Screenshot of current page
            step_description: The verify step's description (what to check)
            test_case_description: Overall test context

        Returns:
            dict with 'success', 'reason', and optionally 'page_issue'
        """

        if self.session_logger:
            self.session_logger.info("🤖 !*!*!* Entering DYNAMIC CONTENT VERIFY prompter: verify_step_visual",
                                     category="ai_routing")

        prompt = f"""You are a QA expert verifying a test step against a screenshot.

## TEST CONTEXT
{test_case_description}

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

**Examples:**
- Description says "Form page with header 'Contact Us'" → PASS if you see a form with "Contact Us" header
- Description says "Tab 'Settings' is active" → PASS if Settings tab appears selected/highlighted
- Description says "Error message is displayed" → FAIL if no error message visible
- Description says "List showing 5 items" → PASS if list shows 5 or more items, FAIL if fewer

**Response if verification PASSED:**
```json
{{
  "success": true,
  "reason": "brief explanation of what key elements were verified"
}}
```

**Response if verification FAILED:**
```json
{{
  "success": false,
  "reason": "what key element is missing or different"
}}
```

Return ONLY valid JSON, nothing else.
"""

        content = [
            {"type": "text", "text": "Screenshot of the current page:"},
            {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": screenshot_base64}},
            {"type": "text", "text": prompt}
        ]

        # Log AI call
        if self.session_logger:
            self.session_logger.ai_call("verify_step_visual", prompt_size=len(screenshot_base64))

        response = self._call_api_with_retry_multimodal(content, max_tokens=300)

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

            # Log verification result
            status = "PASSED" if result.get("success", True) else "FAILED"
            msg = f"!!!! 👁️ Dynamic Content Verify Step: {status} - {result.get('reason', '')[:100]}"
            print(msg)
            if self.session_logger:
                self.session_logger.debug(msg, category="debug_trace")

            return {
                "success": result.get("success", True),
                "reason": result.get("reason", "")
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