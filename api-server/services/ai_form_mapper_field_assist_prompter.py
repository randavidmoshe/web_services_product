# ============================================================================
# Form Mapper - AI Field Assist Prompter
# ============================================================================
# Lightweight AI queries for field-specific checks during step execution.
# Uses vision to analyze screenshots and answer simple YES/NO questions.
# ============================================================================

import logging
import anthropic
from typing import Dict, Any, Optional
import json
logger = logging.getLogger(__name__)


class AIFieldAssist:
    """
    AI helper for field-specific queries during step execution.
    Designed for lightweight, fast responses (YES/NO answers).
    """

    def __init__(self, api_key: str):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = "claude-sonnet-4-20250514"

    def check_dropdown_visible(self, screenshot_base64: str, step: Dict) -> Dict[str, Any]:
        """
        Check if a dropdown/popup with selectable items is visible for the given field.

        Args:
            screenshot_base64: Base64 encoded screenshot
            step: The step being executed (contains selector, description)

        Returns:
            {"has_valid_options": bool, "reason": str}
        """
        selector = step.get("selector", "")
        description = step.get("description", "")

        prompt = f"""Look at this screenshot. I just typed in a field to trigger autocomplete suggestions.
    
    
    
Field info:
- Selector: {selector}
- Description: {description}

Question: Is there a dropdown/popup visible with SELECTABLE ITEMS (not just "No records found", "Searching...", or similar messages)?

Answer in this exact format:
ANSWER: YES or NO
REASON: (brief explanation - what do you see?)"""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=150,
                messages=[
                    {
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
                    }
                ]
            )

            response_text = response.content[0].text.strip()
            logger.info(f"[AIFieldAssist] check_dropdown_visible response: {response_text}")

            # Parse response
            has_valid_options = "ANSWER: YES" in response_text.upper()
            reason = ""
            if "REASON:" in response_text:
                reason = response_text.split("REASON:")[-1].strip()

            return {
                "has_valid_options": has_valid_options,
                "reason": reason,
                "raw_response": response_text
            }

        except Exception as e:
            logger.error(f"[AIFieldAssist] check_dropdown_visible failed: {e}")
            return {
                "has_valid_options": False,
                "reason": f"Error: {str(e)}",
                "error": True
            }



    def query(self, query_type: str, screenshot_base64: str, step: Dict) -> Dict[str, Any]:
        """
        Route query to appropriate method based on query_type.

        Args:
            query_type: Type of query ("dropdown_visible", etc.)
            screenshot_base64: Base64 encoded screenshot
            step: The step being executed

        Returns:
            Query result dict
        """
        handlers = {
            "dropdown_visible": self.check_dropdown_visible,
        }

        handler = handlers.get(query_type)
        if not handler:
            return {"error": True, "reason": f"Unknown query_type: {query_type}"}

        return handler(screenshot_base64, step)