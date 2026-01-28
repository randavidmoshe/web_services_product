# ai_form_mapper_page_visual_verifier.py
# AI-Powered Visual Page Verification using Claude Vision API
# Verifies form field values on result pages (view page, list page)

import json
import time
import logging
import anthropic
import random
from typing import Dict, List, Optional
from anthropic._exceptions import OverloadedError, APIError

logger = logging.getLogger(__name__)


class PageVisualVerifier:
    """Verifies form field values on result pages by comparing executed steps with page screenshot"""

    def __init__(self, api_key: str, session_logger=None):
        if not api_key:
            raise ValueError("API key is required for AI functionality")
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = "claude-haiku-4-5-20251001"
        self.session_logger = session_logger

    def _call_api_with_retry_multimodal(self, content: list, max_tokens: int = 2048, max_retries: int = 3) -> Optional[
        str]:
        """Call Claude API with retry logic for multimodal content (images + text)"""
        delay = 2

        for attempt in range(max_retries):
            try:
                print(f"[PageVisualVerifier] Calling Claude API with vision (attempt {attempt + 1}/{max_retries})...")

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
                print(f"[PageVisualVerifier] ✅ API call successful ({len(response_text)} chars)")
                return response_text

            except OverloadedError as e:
                if attempt == max_retries - 1:
                    print(f"[PageVisualVerifier] ❌ API Overloaded after {max_retries} attempts. Giving up.")
                    logger.error(f"[PageVisualVerifier] API Overloaded after {max_retries} attempts: {e}")
                    return None

                jitter = random.uniform(0, delay * 0.5)
                wait_time = delay + jitter

                print(f"[PageVisualVerifier] ⚠️ API Overloaded. Retrying in {wait_time:.1f}s...")
                logger.warning(f"[PageVisualVerifier] API Overloaded. Retry {attempt + 1}/{max_retries}")

                time.sleep(wait_time)
                delay *= 2

            except APIError as e:
                if attempt == max_retries - 1:
                    print(f"[PageVisualVerifier] ❌ API Error after {max_retries} attempts: {e}")
                    logger.error(f"[PageVisualVerifier] API Error after {max_retries} attempts: {e}")
                    return None

                print(f"[PageVisualVerifier] ⚠️ API Error: {e}. Retrying...")
                time.sleep(delay)
                delay *= 2

            except Exception as e:
                print(f"[PageVisualVerifier] ❌ Unexpected error: {e}")
                logger.error(f"[PageVisualVerifier] Unexpected error: {e}")
                return None

        return None

    def _log_bug(self, bug: Dict, field_name: str):
        """Log a bug found during verification"""
        if not self.session_logger:
            return

        severity = bug.get("severity", "high")
        bug_type = bug.get("type", "unknown")
        field = bug.get("field", field_name)
        expected = bug.get("expected", "")
        actual = bug.get("actual", "")
        description = bug.get("description", "")

        msg = f"!!! 🐛 BUG [{severity.upper()}] Type: {bug_type} | Field: {field}"
        if description:
            msg += f" | {description}"
        if expected:
            msg += f" | Expected: {expected}"
        if actual:
            msg += f" | Actual: {actual}"

        if severity == "critical":
            self.session_logger.error(msg, category="bug")
        else:
            self.session_logger.warning(msg, category="bug")

    def verify_page(
            self,
            screenshot_base64: str,
            executed_steps: List[Dict],
            already_verified_fields: List[Dict],
            verification_instructions: Optional[str] = None
    ) -> Dict:
        """
        Verify form field values on result page.

        Args:
            screenshot_base64: Base64 encoded screenshot of result page
            executed_steps: List of all executed steps with actions and values
            already_verified_fields: List of fields already verified in previous calls (don't re-verify)
            verification_instructions: Optional user-provided rules for field verification (e.g., "First Name should be preceded by Mr/Mrs")

        Returns:
            Dict with page_ready, page_type, results, reason
        """

        if self.session_logger:
            self.session_logger.info("🤖 !*!*! Entering FORM PAGE MAPPER VISUAL VERIFIER: verify_page", category="ai_routing")

        # Extract fields to verify from executed steps (non-verify actions with values)
        steps_for_ai = []
        for step in executed_steps:
            action = step.get("action", "")
            value = step.get("value", "")
            description = step.get("description", "")

            # Skip verify steps only
            if action == "verify":
                continue

            steps_for_ai.append({
                "field": description or step.get("selector", "unknown"),
                "value": value,
                "action": action
            })

        # Build list of already verified field names
        already_verified_names = [f.get("field", "") for f in already_verified_fields]

        # Build verification instructions section if provided
        verification_instructions_section = ""
        if verification_instructions:
            verification_instructions_section = f"""
**Additional Verification Rules (provided by user):**
{verification_instructions}
"""

        prompt = f"""You are analyzing a screenshot of a web page to verify that form field values were saved correctly.

## FIRST: CHECK FOR VALIDATION ERRORS

Scan the screenshot for validation errors (red boxes, red borders around fields, error messages like "Please fill in", "required", "invalid", "error", warning icons near fields).

**If validation errors are visible, return ONLY:**
```json
{{{{
  "validation_errors_detected": true
}}}}
```

**If NO validation errors:** Continue below.

**Your Task:**
1. First, determine if the page is READY (fully loaded) or NOT READY (still loading/spinning)
2. If ready, identify the PAGE TYPE: "view_page" (detail/record view), "edit_page" (after save the page appears in edit mode), "list_page" (table/grid), or "other"
3. For each field in the list below, verify if the expected value appears on the page

**Page Not Ready Indicators:**
- Spinning/loading indicators
- "Please wait" or "Loading..." messages
- Grayed out or skeleton content
- Progress bars

**Full Executed Steps (in order - includes clicks, tabs, field fills, etc.):**
{json.dumps(steps_for_ai, indent=2)}

**Already Reported Failures (don't report these again, mark as already_sent=true):**
{json.dumps(already_verified_names, indent=2)}

**Verification Rules:**
- For each field, check if the value appears on the page
{verification_instructions_section}
- The value might appear in a table cell, a read-only field, a label, or text
- Think like a human QA tester, not a string comparison tool

**PASS these cases (acceptable formatting differences):**
- Honorific prefixes: "John Doe" matches "Mr John Doe", "Dr. John Doe", "Mrs Jane Smith"
- Extra whitespace or trimming differences
- Case differences for non-name fields
- Date format differences: "2024-01-15" matches "Jan 15, 2024" or "15/01/2024"
- Currency formatting: "1000" matches "$1,000.00" or "1,000 USD"
- Phone formatting: "5551234567" matches "(555) 123-4567" or "555-123-4567"
- Partial match for long text (first significant part matching is OK)

**FAIL these cases (actual bugs):**
- Typos in prefix: "Mis John Doe" (should be Miss/Mrs) - this is a BUG
- Formatting/punctuation bugs: "Mr., John Doe" (wrong comma), "John , Doe" (misplaced space/comma)
- Double spaces or weird spacing: "John  Doe" or "John Doe "
- Wrong concatenation: "JohnDoe" (missing space) or "John-Doe" (wrong separator)
- Corrupted/garbled text: "J0hn D@e" or "John Doe???"
- Truncated values: expected "John Doe" but got "John D" or "John..."
- Wrong value entirely: expected "John Doe" but got "Jane Smith"
- Missing value: field is empty or shows placeholder like "N/A", "--", "null"
- Extra garbage characters: "John Doe###" or "John Doe [object Object]"
- Encoding issues: "John Doe" shows as "John Doeâ€™" or similar

**Key principle:** If a human would say "that looks correct" → PASS. If a human would say "that's a bug" → FAIL with clear reason.

**Order and Position Verification:**
You have the full list of executed steps in order. Use this context to verify:
- Fields filled under a specific tab/section should appear under that same section in results
- Relative order should make sense: if First Name was filled before Last Name, First Name should not appear after Last Name in results
- If steps show clicking "Tab 1" then filling fields, then clicking "Tab 2" then filling more fields - verify Tab 1 fields appear in Tab 1 section and Tab 2 fields appear in Tab 2 section

If a field appears in the wrong section/tab or in wrong order relative to other fields → FAIL with reason describing the position issue (e.g., "Last Name appears above First Name" or "Email appears under Address tab instead of Contact tab")

***Response Format - return ONLY valid JSON:**
{{
  "page_ready": true/false,
  "page_type": "view_page" | "list_page" | "edit_page" | "other",
  "results": [
    {{
      "field": "field description",
      "expected": "expected value",
      "status": "passed" | "failed",
      "actual": "what was actually found on page",
      "severity": "critical" | "high" | "medium",
      "type": "missing_value" | "wrong_value" | "formatting_bug" | "truncated" | "wrong_position",
      "description": "brief description of the specific issue",
      "already_sent": true/false
    }}
  ]
}}

**Severity Guidelines:**
- critical: Value completely missing or shows error
- high: Wrong value or major formatting bug
- medium: Minor formatting issue or position issue

**Important:**
- Set page_ready=false ONLY if page is still loading
- Set already_sent=true for fields that were in the "Already Verified Fields" list

**PAGE TYPE SPECIFIC RULES:**

For "view_page" (detail/record view) or "edit_page" (after save the page is in edit mode):
- Verify ALL fields from the executed steps
- If a field's value is not visible, set status="failed" with reason="not found on page"

For "list_page" (table/grid):
- First, find the ROW that corresponds to our form submission (look for any of the expected values in a row)
- ONLY verify fields that are actually VISIBLE AS COLUMNS in the grid
- SKIP fields that are not shown as columns - do NOT report them as failures
- Only include results for fields that have a corresponding column in the grid
- If you find our row and a visible column shows wrong data → FAIL
- If you find our row and visible columns show correct data → PASS
- If you cannot find a row with our data at all → FAIL with reason="row not found in list"
"""

        # Build multimodal content
        content = [
            {
                "type": "text",
                "text": "Screenshot of the result page after form submission:"
            },
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

        response = self._call_api_with_retry_multimodal(content, max_tokens=2048)

        # Log raw AI response
        if response:
            msg = f"!!!! 👁️ Page Visual Verify RAW AI Response: {response[:500]}..."
            print(msg)
            if self.session_logger:
                self.session_logger.debug(msg, category="debug_trace")

        if not response:
            # Default to page ready if AI fails (don't block)
            return {
                "page_ready": True,
                "page_type": "unknown",
                "results": [],
                "reason": "AI verification failed - continuing without verification"
            }

        # Parse response
        try:
            # Clean response - remove markdown if present
            cleaned = response.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()

            result = json.loads(cleaned)

            # Log each failed field
            results = result.get("results", [])
            failed_count = 0
            for field_result in results:
                if field_result.get("status") == "failed" and not field_result.get("already_sent"):
                    self._log_bug(field_result, field_result.get("field", "unknown"))
                    failed_count += 1

            # Log summary
            if failed_count > 0:
                msg = f"!!! ❌ Form Page Verify: {failed_count} field(s) failed"
                print(msg)
                if self.session_logger:
                    self.session_logger.warning(msg, category="verification_result")
            else:
                passed_count = len([r for r in results if r.get("status") == "passed"])
                msg = f"!!! ✅ Form Page Verify: {passed_count} field(s) passed"
                print(msg)
                if self.session_logger:
                    self.session_logger.info(msg, category="verification_result")

            return {
                "page_ready": result.get("page_ready", True),
                "page_type": result.get("page_type", "unknown"),
                "results": results,
                "reason": result.get("reason", "")
            }
        except json.JSONDecodeError as e:
            logger.error(f"[PageVisualVerifier] Failed to parse response: {e}")
            logger.error(f"[PageVisualVerifier] Response was: {response[:500]}")
            # Default to page ready if parsing fails
            return {
                "page_ready": True,
                "page_type": "unknown",
                "results": [],
                "reason": f"Failed to parse AI response - continuing without verification"
            }


def create_page_visual_verifier(api_key: str, session_logger=None) -> PageVisualVerifier:
    """Factory function to create PageVisualVerifier instance"""
    return PageVisualVerifier(api_key, session_logger)