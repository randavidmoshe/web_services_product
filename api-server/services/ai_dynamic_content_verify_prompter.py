# services/ai_dynamic_content_verify_prompter.py
# AI-Powered Visual Verification for Dynamic Content Testing
# Image-only verification (no DOM needed)

import json
import time
import logging
import anthropic
import random
from typing import Optional
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

    def _call_api_with_retry_multimodal(self, content: list, max_tokens: int = 1000, max_retries: int = 3) -> Optional[str]:
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

    def verify_visual(
            self,
            screenshot_base64: str,
            test_case_description: str = ""
    ) -> str:
        """
        Visual verification of page state for dynamic content.
        Returns UI issue string if found, empty string if OK.

        Args:
            screenshot_base64: Screenshot of current page
            test_case_description: Context about what we're testing

        Returns:
            Empty string if page looks OK, otherwise description of issue
        """

        if self.session_logger:
            self.session_logger.info("🤖 !*!*!* Entering DYNAMIC CONTENT VERIFY prompter: verify_visual", category="ai_routing")

        prompt = f"""You are a QA expert analyzing a screenshot of a web page.

## CONTEXT
Test case: {test_case_description}

## YOUR TASK
Check if the page shows any UI issues that would prevent testing:

1. **Error states**: 404, 500 errors, "Page not found", crash messages
2. **Login issues**: "Session expired", "Please log in", authentication errors
3. **Loading stuck**: Infinite spinners, "Loading..." that seems stuck
4. **Broken layout**: Major visual bugs, overlapping elements, blank page
5. **Access denied**: Permission errors, "Forbidden", "Unauthorized"

## RESPONSE

If the page looks READY FOR TESTING (no blocking issues):
Return exactly: OK

If there's a BLOCKING ISSUE:
Return a brief description of the issue (max 100 chars)
Example: "Page shows 404 Not Found error"
Example: "Login session expired - redirected to login page"
Example: "Page is blank - content failed to load"

Return ONLY "OK" or the issue description, nothing else.
"""

        content = [
            {
                "type": "text",
                "text": "Screenshot of the current page:"
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

        response = self._call_api_with_retry_multimodal(content, max_tokens=200)

        if not response:
            # If AI fails, assume page is OK (don't block)
            return ""

        response = response.strip()

        if response.upper() == "OK":
            return ""

        # Return the issue description
        return response[:200]