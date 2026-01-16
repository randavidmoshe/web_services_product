# ai_error_recovery.py
# AI-Powered Error Recovery and Alert Handling using Claude API

import json
import time
import logging
import anthropic
import random
import re
from typing import List, Dict, Optional, Any
from anthropic._exceptions import OverloadedError, APIError

logger = logging.getLogger('init_logger.form_page_test')
result_logger_gui = logging.getLogger('init_result_logger_gui.form_page_test')


class AIErrorRecovery:
    """Helper class for AI-powered error recovery and alert handling using Claude API"""
    
    def __init__(self, api_key: str, session_logger=None):
        if not api_key:
            raise ValueError("API key is required for AI functionality")
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = "claude-sonnet-4-5-20250929"
        self.session_logger = session_logger  # For debug mode logging
    
    def _call_api_with_retry(self, prompt: str, max_tokens: int = 4000, max_retries: int = 3) -> Optional[str]:
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
                print(f"[AIErrorRecovery] Calling Claude API (attempt {attempt + 1}/{max_retries})...")
                result_logger_gui.info(f"[AIErrorRecovery] Calling Claude API (attempt {attempt + 1}/{max_retries})...")
                
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
                print(f"[AIErrorRecovery] ✅ API call successful ({len(response_text)} chars)")
                return response_text
                
            except OverloadedError as e:
                if attempt == max_retries - 1:
                    # Last attempt failed
                    print(f"[AIErrorRecovery] ❌ API Overloaded after {max_retries} attempts. Giving up.")
                    logger.error(f"[AIErrorRecovery] API Overloaded after {max_retries} attempts: {e}")
                    return None
                
                # Add jitter to prevent thundering herd
                jitter = random.uniform(0, delay * 0.5)
                wait_time = delay + jitter
                
                print(f"[AIErrorRecovery] ⚠️  API Overloaded (529). Retrying in {wait_time:.1f}s... ({attempt + 1}/{max_retries})")
                logger.warning(f"[AIErrorRecovery] API Overloaded. Retry {attempt + 1}/{max_retries} after {wait_time:.1f}s")
                
                time.sleep(wait_time)
                delay *= 2  # Exponential backoff
                
            except APIError as e:
                if attempt == max_retries - 1:
                    print(f"[AIErrorRecovery] ❌ API Error after {max_retries} attempts: {e}")
                    logger.error(f"[AIErrorRecovery] API Error after {max_retries} attempts: {e}")
                    return None
                
                print(f"[AIErrorRecovery] ⚠️  API Error: {e}. Retrying in {delay}s... ({attempt + 1}/{max_retries})")
                logger.warning(f"[AIErrorRecovery] API Error. Retry {attempt + 1}/{max_retries} after {delay}s")
                
                time.sleep(delay)
                delay *= 2
                
            except Exception as e:
                print(f"[AIErrorRecovery] ❌ Unexpected error: {e}")
                logger.error(f"[AIErrorRecovery] Unexpected error: {e}")
                return None
        
        return None
    
    def _call_api_with_retry_multimodal(self, content: list, max_tokens: int = 4000, max_retries: int = 3) -> Optional[str]:
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
                print(f"[AIErrorRecovery] Calling Claude API with vision (attempt {attempt + 1}/{max_retries})...")
                result_logger_gui.info(f"[AIErrorRecovery] Calling Claude API with vision (attempt {attempt + 1}/{max_retries})...")
                
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
                print(f"[AIErrorRecovery] ✅ API call successful ({len(response_text)} chars)")
                return response_text
                
            except OverloadedError as e:
                if attempt == max_retries - 1:
                    print(f"[AIErrorRecovery] ❌ API Overloaded after {max_retries} attempts. Giving up.")
                    logger.error(f"[AIErrorRecovery] API Overloaded after {max_retries} attempts: {e}")
                    return None
                
                jitter = random.uniform(0, delay * 0.5)
                wait_time = delay + jitter
                
                print(f"[AIErrorRecovery] ⚠️  API Overloaded (529). Retrying in {wait_time:.1f}s... ({attempt + 1}/{max_retries})")
                logger.warning(f"[AIErrorRecovery] API Overloaded. Retry {attempt + 1}/{max_retries} after {wait_time:.1f}s")
                
                time.sleep(wait_time)
                delay *= 2
                
            except APIError as e:
                if attempt == max_retries - 1:
                    print(f"[AIErrorRecovery] ❌ API Error after {max_retries} attempts: {e}")
                    logger.error(f"[AIErrorRecovery] API Error after {max_retries} attempts: {e}")
                    return None
                
                print(f"[AIErrorRecovery] ⚠️  API Error: {e}. Retrying in {delay}s... ({attempt + 1}/{max_retries})")
                logger.warning(f"[AIErrorRecovery] API Error. Retry {attempt + 1}/{max_retries} after {delay}s")
                
                time.sleep(delay)
                delay *= 2
                
            except Exception as e:
                print(f"[AIErrorRecovery] ❌ Unexpected error: {e}")
                logger.error(f"[AIErrorRecovery] Unexpected error: {e}")
                return None
        
        return None

    def analyze_error(
        self,
        error_info: Dict,
        executed_steps: List[Dict],
        dom_html: str,
        screenshot_base64: Optional[str] = None,
        gathered_error_info: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Analyze an error (alert or validation error) and determine how to handle it.
        
        This method does NOT generate steps - it only classifies the error:
        - Scenario A: Simple alert (not a validation error)
        - Scenario B real_issue: Validation error but we filled the field correctly (system bug)
        - Scenario B ai_issue: Validation error because we missed/incorrectly filled a field
        
        Args:
            error_info: Dict with 'type' ('alert' or 'validation_error') and 'text'
            executed_steps: Steps completed before error appeared
            dom_html: Current DOM HTML
            screenshot_base64: Optional screenshot
            gathered_error_info: Optional dict with 'error_fields' and 'error_messages' from DOM detection
            
        Returns:
            Dict with scenario classification and relevant details
        """
        try:
            print(f"[AIErrorRecovery] Analyzing error...")
            
            # Build the prompt
            prompt = self._build_error_analysis_prompt(
                error_info=error_info,
                executed_steps=executed_steps,
                dom_html=dom_html,
                gathered_error_info=gathered_error_info
            )
            
            result_logger_gui.info("[AIErrorRecovery] Sending error analysis request to Claude API...")
            
            # Build message content
            message_content = []
            
            # Add screenshot if available
            if screenshot_base64:
                message_content.append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/png",
                        "data": screenshot_base64
                    }
                })
            
            # Add text prompt
            message_content.append({
                "type": "text",
                "text": prompt
            })
            
            # Call API
            # Debug mode: log full prompt (DOM truncated)
            if self.session_logger and self.session_logger.debug_mode:
                import re
                prompt_for_log = re.sub(r'## Current DOM.*?(?=\n##|\n\*\*|$)', '## Current DOM\n[DOM TRUNCATED]\n\n',
                                        prompt, flags=re.DOTALL)
                self.session_logger.ai_call("analyze_error", prompt_size=len(prompt), prompt=prompt_for_log)

            if screenshot_base64:
                response_text = self._call_api_with_retry_multimodal(message_content, max_tokens=4000, max_retries=3)
            else:
                response_text = self._call_api_with_retry(prompt, max_tokens=4000, max_retries=3)
            
            if response_text is None:
                print("[AIErrorRecovery] ❌ Failed to get error analysis response after retries")
                logger.error("[AIErrorRecovery] Failed to get error analysis response after retries")
                return {"scenario": "B", "issue_type": "api_error", "explanation": "Failed to get API response"}
            
            print(f"[AIErrorRecovery] Received error analysis response ({len(response_text)} chars)")
            logger.info(f"[AIErrorRecovery] Received error analysis response ({len(response_text)} chars)")
            # Debug mode: log full raw response
            if self.session_logger and self.session_logger.debug_mode:
                self.session_logger.ai_response("analyze_error", success=True, response=response_text)

            # Extract JSON from response
            json_match = re.search(r'\{[\s\S]*\}', response_text)
            if json_match:
                json_str = json_match.group()
                # Sanitize invalid escape sequences (e.g., \E, \T, etc.)
                json_str = re.sub(r'\\([^"\\/bfnrtu])', r'\\\\\1', json_str)
                response = json.loads(json_str)
                
                scenario = response.get("scenario", "B")
                
                if scenario == "A":
                    print(f"[AIErrorRecovery] Scenario A: Simple alert (not validation error)")
                    logger.info(f"[AIErrorRecovery] Scenario A: Simple alert")
                    return {"scenario": "A"}
                
                elif scenario == "B":
                    issue_type = response.get("issue_type", "ai_issue")
                    
                    if issue_type == "real_issue":
                        print(f"[AIErrorRecovery] Scenario B: real_issue - System Bug")
                        print(f"[AIErrorRecovery] Explanation: {response.get('explanation', '')}")
                        logger.warning(f"[AIErrorRecovery] Real issue detected: {response.get('explanation', '')}")
                        
                        return {
                            "scenario": "B",
                            "issue_type": "real_issue",
                            "explanation": response.get("explanation", ""),
                            "problematic_field_claimed": response.get("problematic_field_claimed", ""),
                            "our_action": response.get("our_action", ""),
                            "problematic_fields": response.get("problematic_fields", [])
                        }
                    
                    else:  # ai_issue
                        print(f"[AIErrorRecovery] Scenario B: ai_issue - We missed something")
                        print(f"[AIErrorRecovery] Problematic fields: {response.get('problematic_fields', [])}")
                        print(f"[AIErrorRecovery] Field requirements: {response.get('field_requirements', '')}")
                        logger.info(f"[AIErrorRecovery] AI issue - problematic fields: {response.get('problematic_fields', [])}")
                        
                        return {
                            "scenario": "B",
                            "issue_type": "ai_issue",
                            "explanation": response.get("explanation", ""),
                            "problematic_fields": response.get("problematic_fields", []),
                            "field_requirements": response.get("field_requirements", "")
                        }
                else:
                    print(f"[AIErrorRecovery] Unknown scenario: {scenario}")
                    return {"scenario": "B", "issue_type": "ai_issue", "problematic_fields": [], "field_requirements": ""}
            else:
                print("[AIErrorRecovery] No JSON object found in response")
                logger.warning("[AIErrorRecovery] No JSON object found in response")
                return {"scenario": "B", "issue_type": "parse_error", "explanation": "No JSON in response"}
                
        except Exception as e:
            print(f"[AIErrorRecovery] Error analyzing error: {e}")
            logger.error(f"[AIErrorRecovery] Error analyzing error: {e}")
            return {"scenario": "B", "issue_type": "parse_error", "explanation": str(e)}
    
    def _build_error_analysis_prompt(
        self,
        error_info: Dict,
        executed_steps: List[Dict],
        dom_html: str,
        gathered_error_info: Optional[Dict] = None
    ) -> str:
        """Build the prompt for error analysis"""
        
        error_type = error_info.get('type', 'alert')
        error_text = error_info.get('text', '')
        
        # Build executed steps context - this is CRITICAL for determining real_issue vs ai_issue
        executed_steps_json = json.dumps([
            {
                "step": i+1, 
                "action": s.get("action"), 
                "selector": s.get("selector"), 
                "value": s.get("value"),
                "description": s.get("description")
            } 
            for i, s in enumerate(executed_steps)
        ], indent=2)
        
        # Build gathered error info section if provided
        gathered_info_section = ""
        if gathered_error_info:
            error_fields = gathered_error_info.get("error_fields", [])
            error_messages = gathered_error_info.get("error_messages", [])
            if error_fields or error_messages:
                gathered_info_section = f"""
## Additional Error Information (from DOM analysis):
- Error Fields Detected: {', '.join(error_fields) if error_fields else 'None'}
- Error Messages Detected: {', '.join(error_messages) if error_messages else 'None'}
"""
        
        prompt = f"""# ERROR ANALYSIS TASK

## Your Goal
Analyze the error and classify it into one of three categories. You do NOT need to generate any steps.

## Error Information
- **Type**: {error_type}
- **Message**: "{error_text}"
{gathered_info_section}

## Steps We Already Executed
```json
{executed_steps_json}
```

## Current DOM
```html
{dom_html}
```

---

## DECISION PROCESS

### Step 1: Is this a validation error?

Check if the error message complains about:
- Missing/required fields
- Invalid field values
- Format errors (wrong length, wrong characters, etc.)

**If NO** (just a confirmation, success message, warning, or generic notification):
→ Return **Scenario A**

**If YES** (validation error about fields):
→ Continue to Step 2

### Step 2: Check executed_steps - Did we fill the problematic field(s)?

For EACH field mentioned in the error:
1. Search the executed_steps list for any step that filled this field
2. Look for matching selectors (e.g., if error mentions "Email", look for selectors like `#email`, `input[name="email"]`, `[id*="email"]`, etc.)
3. Check if the value we used was valid

**Decision:**
- If we DID fill the field with a valid value → **real_issue** (system bug - it falsely claims field is missing)
- If we did NOT fill the field, or used invalid value → **ai_issue** (we made a mistake)

---

## RESPONSE FORMAT

Return ONLY a JSON object (no other text):

**For Scenario A** (not a validation error):
```json
{{
  "scenario": "A"
}}
```

**For Scenario B - real_issue** (we filled correctly, system bug):
```json
{{
  "scenario": "B",
  "issue_type": "real_issue",
  "explanation": "Error claims [field] is required, but we filled it at step [N] with selector [selector] and value [value]",
  "problematic_field_claimed": "Field name from error message",
  "our_action": "Step N: filled [selector] with [value]",
  "problematic_fields": ["Field name"]
}}
```

**For Scenario B - ai_issue** (we missed or made a mistake):
```json
{{
  "scenario": "B",
  "issue_type": "ai_issue",
  "explanation": "We missed filling [field] / We used invalid value for [field]",
  "problematic_fields": ["Field1", "Field2"],
  "field_requirements": "1. Field1 - exact requirement (e.g., must be 20 digits)\\n2. Field2 - exact requirement"
}}
```

Return ONLY the JSON object.
"""
        
        return prompt

    # Keep old method name for backward compatibility
    def regenerate_steps_after_alert(
        self,
        alert_info: Dict,
        executed_steps: List[Dict],
        dom_html: str,
        screenshot_base64: Optional[str],
        test_cases: List[Dict],
        test_context,
        step_where_alert_appeared: int,
        include_accept_step: bool = True,
        gathered_error_info: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Backward compatible wrapper - calls analyze_error internally.
        
        Note: test_cases, test_context, step_where_alert_appeared, and include_accept_step
        are no longer used since we don't generate steps anymore.
        """
        # Convert alert_info format if needed
        error_info = {
            'type': alert_info.get('type', alert_info.get('alert_type', 'alert')),
            'text': alert_info.get('text', alert_info.get('alert_text', ''))
        }
        
        return self.analyze_error(
            error_info=error_info,
            executed_steps=executed_steps,
            dom_html=dom_html,
            screenshot_base64=screenshot_base64,
            gathered_error_info=gathered_error_info
        )

    def analyze_validation_errors(
            self,
            executed_steps: List[Dict],
            dom_html: str,
            screenshot_base64: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze validation errors visible in DOM/screenshot (red borders, error messages, etc.)

        This method does NOT generate steps - it only classifies the error:
        - Scenario B real_issue: We filled the field correctly but system shows error (system bug)
        - Scenario B ai_issue: We missed/incorrectly filled a field (our mistake)

        Args:
            executed_steps: Steps completed before errors appeared
            dom_html: Current DOM HTML with validation errors
            screenshot_base64: Optional screenshot showing the errors

        Returns:
            Dict with scenario classification and relevant details
        """
        try:
            print(f"[AIErrorRecovery] Analyzing validation errors...")

            # Build the prompt
            prompt = self._build_validation_error_prompt(
                executed_steps=executed_steps,
                dom_html=dom_html
            )

            result_logger_gui.info("[AIErrorRecovery] Sending validation error analysis request to Claude API...")

            # Build message content
            message_content = []

            # Add screenshot if available
            if screenshot_base64:
                message_content.append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/png",
                        "data": screenshot_base64
                    }
                })

            # Add text prompt
            message_content.append({
                "type": "text",
                "text": prompt
            })

            # Call API
            # Debug mode: log full prompt (DOM truncated)
            if self.session_logger and self.session_logger.debug_mode:
                #import re
                prompt_for_log = re.sub(r'## Current DOM.*?(?=\n##|\n\*\*|$)', '## Current DOM\n[DOM TRUNCATED]\n\n',
                                        prompt, flags=re.DOTALL)
                self.session_logger.ai_call("analyze_validation_errors", prompt_size=len(prompt), prompt=prompt_for_log)

            if screenshot_base64:
                response_text = self._call_api_with_retry_multimodal(message_content, max_tokens=4000,
                                                                     max_retries=3)
            else:
                response_text = self._call_api_with_retry(prompt, max_tokens=4000, max_retries=3)

            if response_text is None:
                print("[AIErrorRecovery] ❌ Failed to get validation error analysis response after retries")
                logger.error("[AIErrorRecovery] Failed to get validation error analysis response after retries")
                return {"scenario": "B", "issue_type": "api_error", "explanation": "Failed to get API response"}

            print(f"[AIErrorRecovery] Received validation error analysis response ({len(response_text)} chars)")
            logger.info(
                f"[AIErrorRecovery] Received validation error analysis response ({len(response_text)} chars)")

            # Debug mode: log full raw response
            if self.session_logger and self.session_logger.debug_mode:
                self.session_logger.ai_response("analyze_validation_errors", success=True, response=response_text)

            # Extract JSON from response
            json_match = re.search(r'\{[\s\S]*\}', response_text)
            if json_match:
                json_str = json_match.group()
                # Sanitize invalid escape sequences
                json_str = re.sub(r'\\([^"\\/bfnrtu])', r'\\\\\1', json_str)
                response = json.loads(json_str)

                issue_type = response.get("issue_type", "ai_issue")

                if issue_type == "real_issue":
                    print(f"[AIErrorRecovery] Validation Error: real_issue - System Bug")
                    print(f"[AIErrorRecovery] Explanation: {response.get('explanation', '')}")
                    logger.warning(f"[AIErrorRecovery] Real issue detected: {response.get('explanation', '')}")

                    return {
                        "scenario": "B",
                        "issue_type": "real_issue",
                        "explanation": response.get("explanation", ""),
                        "problematic_field_claimed": response.get("problematic_field_claimed", ""),
                        "our_action": response.get("our_action", ""),
                        "problematic_fields": response.get("problematic_fields", [])
                    }

                else:  # ai_issue
                    print(f"[AIErrorRecovery] Validation Error: ai_issue - We missed something")
                    print(f"[AIErrorRecovery] Problematic fields: {response.get('problematic_fields', [])}")
                    print(f"[AIErrorRecovery] Field requirements: {response.get('field_requirements', '')}")
                    logger.info(
                        f"[AIErrorRecovery] AI issue - problematic fields: {response.get('problematic_fields', [])}")

                    return {
                        "scenario": "B",
                        "issue_type": "ai_issue",
                        "explanation": response.get("explanation", ""),
                        "problematic_fields": response.get("problematic_fields", []),
                        "field_requirements": response.get("field_requirements", "")
                    }
            else:
                print("[AIErrorRecovery] No JSON object found in response")
                logger.warning("[AIErrorRecovery] No JSON object found in response")
                return {"scenario": "B", "issue_type": "parse_error", "explanation": "No JSON in response"}

        except Exception as e:
            print(f"[AIErrorRecovery] Error analyzing validation errors: {e}")
            logger.error(f"[AIErrorRecovery] Error analyzing validation errors: {e}")
            return {"scenario": "B", "issue_type": "parse_error", "explanation": str(e)}

    def _build_validation_error_prompt(
            self,
            executed_steps: List[Dict],
            dom_html: str
    ) -> str:
        """Build the prompt for validation error analysis"""

        # Build executed steps context
        executed_steps_json = json.dumps([
            {
                "step": i + 1,
                "action": s.get("action"),
                "selector": s.get("selector"),
                "value": s.get("value"),
                "description": s.get("description")
            }
            for i, s in enumerate(executed_steps)
        ], indent=2)

        prompt = f"""# VALIDATION ERROR ANALYSIS

## Your Goal
The page is showing validation errors (red borders, error messages, etc.). Analyze these errors and determine if they are caused by a system bug or by our mistake.

## Steps We Already Executed
```json
{executed_steps_json}
```

## Current DOM (with validation errors visible)
```html
{dom_html}
```

---

## YOUR TASK

### Step 1: Find All Validation Errors

Scan the DOM and screenshot for:
- Fields with error classes: `error`, `invalid`, `has-error`, `is-invalid`, `field-error`, `ng-invalid`, `validation-error`
- Error message elements near fields
- Attributes: `aria-invalid="true"`, `data-error="true"`
- Red border styles
- Error text/icons in screenshot

List all fields that have errors.

### Step 2: For Each Error Field - Check Executed Steps

For EACH field with an error:
1. Search executed_steps for any step that filled this field
2. Look for matching selectors (e.g., if error is on "Email" field, look for `#email`, `input[name="email"]`, etc.)
3. Check if the value we used was valid

### Step 3: Determine Issue Type

**CRITICAL:** If the error specifies a requirement and our value does NOT meet that requirement - it is ALWAYS **ai_issue**.

**real_issue** (System Bug):
- We filled the field with a value that MEETS the stated requirement in the error message
- But system still shows error
- The validation is incorrectly rejecting valid input

**ai_issue** (Our Mistake):
- We did NOT fill the field
- OR our value does NOT meet the requirement stated in the error message (wrong length, wrong format, missing characters, etc.)
- We need to retry with a value that meets the requirement

---

## RESPONSE FORMAT

Return ONLY a JSON object:

**For real_issue** (we filled correctly, system bug):
```json
{{
  "issue_type": "real_issue",
  "explanation": "Field [X] shows error, but we filled it at step [N] with selector [selector] and value [value]. The validation is incorrectly rejecting valid input.",
  "problematic_field_claimed": "Field name showing error",
  "our_action": "Step N: filled [selector] with [value]",
  "problematic_fields": ["Field name"]
}}
```

**For ai_issue** (we missed or made mistake):
```json
{{
  "issue_type": "ai_issue",
  "explanation": "We missed filling [field] / We used invalid value for [field]",
  "problematic_fields": ["Field1", "Field2"],
  "field_requirements": "1. Field1 - exact requirement\\n2. Field2 - exact requirement"
}}
```

Return ONLY the JSON object.
"""

        return prompt