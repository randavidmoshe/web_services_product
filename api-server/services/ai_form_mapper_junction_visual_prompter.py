# ai_form_mapper_junction_visual_prompter.py
# AI-Powered Junction Visual Verification using Claude Vision API

import json
import time
import logging
import anthropic
import random
from typing import Dict, Optional
from anthropic._exceptions import OverloadedError, APIError

logger = logging.getLogger(__name__)


class JunctionVisualVerifier:
    """Verifies if a junction step actually revealed new form fields by comparing before/after screenshots"""

    def __init__(self, api_key: str, session_logger=None):
        if not api_key:
            raise ValueError("API key is required for AI functionality")
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = "claude-haiku-4-5-20251001"
        self.session_logger = session_logger

    def _call_api_with_retry_multimodal(self, content: list, max_tokens: int = 1024, max_retries: int = 3) -> Optional[
        str]:
        """Call Claude API with retry logic for multimodal content (images + text)"""
        delay = 2

        for attempt in range(max_retries):
            try:
                print(
                    f"[JunctionVisualVerifier] Calling Claude API with vision (attempt {attempt + 1}/{max_retries})...")

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
                print(f"[JunctionVisualVerifier] ✅ API call successful ({len(response_text)} chars)")
                return response_text

            except OverloadedError as e:
                if attempt == max_retries - 1:
                    print(f"[JunctionVisualVerifier] ❌ API Overloaded after {max_retries} attempts. Giving up.")
                    logger.error(f"[JunctionVisualVerifier] API Overloaded after {max_retries} attempts: {e}")
                    return None

                jitter = random.uniform(0, delay * 0.5)
                wait_time = delay + jitter

                print(f"[JunctionVisualVerifier] ⚠️ API Overloaded. Retrying in {wait_time:.1f}s...")
                logger.warning(f"[JunctionVisualVerifier] API Overloaded. Retry {attempt + 1}/{max_retries}")

                time.sleep(wait_time)
                delay *= 2

            except APIError as e:
                if attempt == max_retries - 1:
                    print(f"[JunctionVisualVerifier] ❌ API Error after {max_retries} attempts: {e}")
                    logger.error(f"[JunctionVisualVerifier] API Error after {max_retries} attempts: {e}")
                    return None

                print(f"[JunctionVisualVerifier] ⚠️ API Error: {e}. Retrying...")
                time.sleep(delay)
                delay *= 2

            except Exception as e:
                print(f"[JunctionVisualVerifier] ❌ Unexpected error: {e}")
                logger.error(f"[JunctionVisualVerifier] Unexpected error: {e}")
                return None

        return None

    def verify_junction(
            self,
            before_screenshot: str,
            after_screenshot: str,
            step_info: Dict
    ) -> Dict:
        """
        Compare before/after screenshots to determine if new fields appeared.

        Args:
            before_screenshot: Base64 encoded screenshot before the action
            after_screenshot: Base64 encoded screenshot after the action
            step_info: Information about the step (action, selector, value, description, junction_info)

        Returns:
            Dict with is_junction (bool) and reason (str)
        """
        action = step_info.get("action", "")
        selector = step_info.get("selector", "")
        value = step_info.get("value", "")
        description = step_info.get("description", "")
        junction_info = step_info.get("junction_info", {})

        prompt = f"""You are analyzing two screenshots of a web form to determine if a field is a TRUE JUNCTION.

**What is a Junction?**
A junction is a field (dropdown, radio buttons, etc.) where DIFFERENT options reveal DIFFERENT sets of form fields.
The key question: Would selecting a DIFFERENT option reveal DIFFERENT fields?

**TRUE JUNCTION:**
- Different options show completely different field sets
- The revealed fields are specific/relevant to the selected option
- Selecting another option would show a different form section

**NOT A JUNCTION (parent-child/cascading dependency):**
- A parent field reveals a child field that ALL options would reveal
- Only one dependent dropdown appeared (like a sub-selection)
- The revealed field is generic and would appear regardless of which option was selected
- Classic example: A location dropdown revealing a sub-location dropdown - this happens for ANY selection

**Action performed:**
- Action: {action}
- Selector: {selector}
- Value selected: {value}
- Description: {description}
- Junction info: {json.dumps(junction_info)}

***Your task:**
Compare the BEFORE screenshot (first image) with the AFTER screenshot (second image).

Ask yourself: Are the new fields SPECIFIC to this option, or would ANY option reveal the same dependent field?

**Signs of TRUE JUNCTION:**
- Multiple new fields appeared that are contextually related to the specific selection
- The new fields represent a different "path" through the form
- Field labels suggest they are specific to the chosen option

**Signs of NOT A JUNCTION:**
- Only ONE new dropdown/field appeared
- The new field looks like a generic sub-selection or child of the parent
- The new field would logically appear for ANY option selected

**Do NOT count as new fields:**
- The same field with a different selected value
- Validation messages or error text
- Minor styling changes, loading indicators, tooltips

**Response format - return ONLY valid JSON:**
{{
  "is_junction": true/false,
  "reason": "Brief explanation - true junction with option-specific fields, or just a parent-child dependency?",
  "new_fields_detected": ["list of new field descriptions if any"]
}}

Set is_junction to TRUE only if different options would show DIFFERENT fields.
Set is_junction to FALSE if this is a parent-child dependency where any option reveals the same child field."""

        # Build multimodal content
        content = [
            {
                "type": "text",
                "text": "BEFORE screenshot (before the selection):"
            },
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/png",
                    "data": before_screenshot
                }
            },
            {
                "type": "text",
                "text": "AFTER screenshot (after the selection):"
            },
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/png",
                    "data": after_screenshot
                }
            },
            {
                "type": "text",
                "text": prompt
            }
        ]

        response = self._call_api_with_retry_multimodal(content, max_tokens=1024)

        if not response:
            # Default to keeping junction if AI fails (safer)
            return {
                "is_junction": True,
                "reason": "AI verification failed - keeping junction flag as precaution",
                "new_fields_detected": []
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
            return {
                "is_junction": result.get("is_junction", True),
                "reason": result.get("reason", ""),
                "new_fields_detected": result.get("new_fields_detected", [])
            }
        except json.JSONDecodeError as e:
            logger.error(f"[JunctionVisualVerifier] Failed to parse response: {e}")
            logger.error(f"[JunctionVisualVerifier] Response was: {response[:500]}")
            # Default to keeping junction if parsing fails
            return {
                "is_junction": True,
                "reason": f"Failed to parse AI response - keeping junction flag as precaution",
                "new_fields_detected": []
            }


def create_junction_visual_verifier(api_key: str, session_logger=None) -> JunctionVisualVerifier:
    """Factory function to create JunctionVisualVerifier instance"""
    return JunctionVisualVerifier(api_key, session_logger)