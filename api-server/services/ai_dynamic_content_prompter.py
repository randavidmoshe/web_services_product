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

## TEST CASE DESCRIPTION
{test_case_description}

## CURRENT PAGE DOM
{dom_html}

## SELECTOR GUIDELINES

**Use CSS selectors (preferred):**
- input[name='search']
- button[data-testid='submit']
- #search-box
- .search-button

**Use XPath when needed:**
- //button[contains(text(), 'Search')]
- //input[@placeholder='Search...']

**Priority:**
1. data-testid, data-qa attributes
2. id, name attributes
3. Unique classes
4. Text content (XPath)

## AVAILABLE ACTIONS

- **click**: Click an element
- **fill**: Type text into input field
- **select**: Select dropdown option
- **check/uncheck**: Checkbox actions
- **hover**: Hover over element
- **scroll**: Scroll page or element
- **wait**: Wait for condition (use sparingly)
- **verify**: Verify element exists/contains text
- **verify_text**: Verify specific text on page
- **verify_url**: Verify current URL contains/matches

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
      "full_xpath": "//input[@name='search']"
    }},
    {{
      "step_number": 2,
      "action": "click",
      "selector": "button[type='submit']",
      "description": "Click search button",
      "full_xpath": "//button[@type='submit']"
    }},
    {{
      "step_number": 3,
      "action": "verify",
      "selector": ".search-results",
      "expected": "Python",
      "description": "Verify search results contain Python"
    }}
  ]
}}
```

## RULES

1. Generate steps that accomplish the test case description
2. Include verify steps to confirm expected outcomes
3. Use robust selectors that won't break easily
4. Keep steps atomic - one action per step
5. Add wait steps only when necessary (after navigation, dynamic content)
6. Include full_xpath as fallback for CSS selectors
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

Return ONLY valid JSON with "steps" array.
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

## FAILED STEP
Action: {failed_step.get('action')}
Selector: {failed_step.get('selector')}
Description: {failed_step.get('description')}
Error: {error_message}

## TEST CASE DESCRIPTION
{test_case_description}

## CURRENT PAGE DOM
{fresh_dom}

## YOUR TASK
1. Analyze why the step failed
2. Generate 1-3 recovery steps to fix the issue
3. If the element doesn't exist, find the correct selector

Return ONLY valid JSON:
```json
{{
  "recovery_steps": [
    {{
      "step_number": 1,
      "action": "...",
      "selector": "...",
      "description": "..."
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
            recovery_steps = result.get("recovery_steps", [])
            print(f"[DynamicContentAI] Generated {len(recovery_steps)} recovery steps")
            return recovery_steps

        except json.JSONDecodeError as e:
            logger.error(f"[DynamicContentAI] Failed to parse recovery response: {e}")
            return []