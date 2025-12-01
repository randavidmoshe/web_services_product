# ============================================================================
# Form Mapper - AI Helpers Service
# ============================================================================
# This module wraps the AI prompters for use in the distributed system.
# Based on the original PyCharm code:
#   - ai_form_mapper_main_prompter.py
#   - ai_form_mapper_alert_recovery_prompter.py
#   - ai_form_mapper_end_prompter.py
#   - ai_form_page_ui_visual_verify_prompter.py
# ============================================================================

import json
import time
import re
import logging
import random
from typing import List, Dict, Optional, Any
import anthropic
from anthropic._exceptions import OverloadedError, APIError

logger = logging.getLogger(__name__)

CLAUDE_MODEL = "claude-sonnet-4-5-20250929"


# ============================================================================
# Base class with retry logic
# ============================================================================

class BaseAIHelper:
    """Base class with common retry logic for Claude API calls"""
    
    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("API key is required for AI functionality")
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = CLAUDE_MODEL
    
    def _call_api_with_retry(
        self, 
        prompt: str, 
        max_tokens: int = 16000, 
        max_retries: int = 3
    ) -> Optional[str]:
        """Call Claude API with retry logic for text-only prompts"""
        delay = 2
        
        for attempt in range(max_retries):
            try:
                logger.info(f"[AI] Calling Claude API (attempt {attempt + 1}/{max_retries})...")
                
                message = self.client.messages.create(
                    model=self.model,
                    max_tokens=max_tokens,
                    messages=[{"role": "user", "content": prompt}]
                )
                
                response_text = message.content[0].text
                logger.info(f"[AI] API call successful ({len(response_text)} chars)")
                return response_text
                
            except OverloadedError as e:
                if attempt == max_retries - 1:
                    logger.error(f"[AI] API Overloaded after {max_retries} attempts: {e}")
                    return None
                
                jitter = random.uniform(0, delay * 0.5)
                wait_time = delay + jitter
                logger.warning(f"[AI] API Overloaded. Retry {attempt + 1}/{max_retries} after {wait_time:.1f}s")
                time.sleep(wait_time)
                delay *= 2
                
            except APIError as e:
                if attempt == max_retries - 1:
                    logger.error(f"[AI] API Error after {max_retries} attempts: {e}")
                    return None
                logger.warning(f"[AI] API Error. Retry {attempt + 1}/{max_retries}")
                time.sleep(delay)
                delay *= 2
                
            except Exception as e:
                logger.error(f"[AI] Unexpected error: {e}")
                return None
        
        return None
    
    def _call_api_with_retry_multimodal(
        self, 
        content: list, 
        max_tokens: int = 16000, 
        max_retries: int = 3
    ) -> Optional[str]:
        """Call Claude API with retry logic for multimodal content (images + text)"""
        delay = 2
        
        for attempt in range(max_retries):
            try:
                logger.info(f"[AI] Calling Claude API with vision (attempt {attempt + 1}/{max_retries})...")
                
                message = self.client.messages.create(
                    model=self.model,
                    max_tokens=max_tokens,
                    messages=[{"role": "user", "content": content}]
                )
                
                response_text = message.content[0].text
                logger.info(f"[AI] API call successful ({len(response_text)} chars)")
                return response_text
                
            except OverloadedError as e:
                if attempt == max_retries - 1:
                    logger.error(f"[AI] API Overloaded after {max_retries} attempts: {e}")
                    return None
                
                jitter = random.uniform(0, delay * 0.5)
                wait_time = delay + jitter
                logger.warning(f"[AI] API Overloaded. Retry after {wait_time:.1f}s")
                time.sleep(wait_time)
                delay *= 2
                
            except APIError as e:
                if attempt == max_retries - 1:
                    logger.error(f"[AI] API Error after {max_retries} attempts: {e}")
                    return None
                logger.warning(f"[AI] API Error. Retry after {delay}s")
                time.sleep(delay)
                delay *= 2
                
            except Exception as e:
                logger.error(f"[AI] Unexpected error: {e}")
                return None
        
        return None


# ============================================================================
# AIFormMapperHelper - Main step generation
# ============================================================================

class AIFormMapperHelper(BaseAIHelper):
    """
    AI Helper for generating and regenerating test steps.
    Based on ai_form_mapper_main_prompter.py
    """
    
    def generate_test_steps(
        self,
        dom_html: str,
        test_cases: List[Dict[str, str]],
        test_context: Optional[Dict] = None,
        screenshot_base64: Optional[str] = None,
        critical_fields_checklist: Optional[Dict[str, str]] = None,
        field_requirements: Optional[str] = None,
        previous_paths: Optional[List[Dict]] = None,
        current_path_junctions: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """
        Generate Selenium test steps based on DOM and test cases.
        
        Returns:
            Dict with 'steps' (list), 'no_more_paths' (bool)
        """
        # Build the prompt (simplified version - your actual prompt is more detailed)
        prompt = self._build_generate_steps_prompt(
            dom_html=dom_html,
            test_cases=test_cases,
            test_context=test_context,
            critical_fields_checklist=critical_fields_checklist,
            field_requirements=field_requirements,
            previous_paths=previous_paths,
            current_path_junctions=current_path_junctions
        )
        
        # Call API with or without screenshot
        if screenshot_base64:
            content = [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/png",
                        "data": screenshot_base64
                    }
                },
                {"type": "text", "text": prompt}
            ]
            response_text = self._call_api_with_retry_multimodal(content)
        else:
            response_text = self._call_api_with_retry(prompt)
        
        if not response_text:
            return {"steps": [], "no_more_paths": False}
        
        # Parse response
        return self._parse_steps_response(response_text)
    
    def regenerate_steps(
        self,
        dom_html: str,
        executed_steps: List[Dict],
        test_cases: List[Dict[str, str]],
        test_context: Optional[Dict] = None,
        screenshot_base64: Optional[str] = None,
        critical_fields_checklist: Optional[Dict[str, str]] = None,
        field_requirements: Optional[str] = None,
        previous_paths: Optional[List[Dict]] = None,
        current_path_junctions: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """
        Regenerate remaining steps after DOM change.
        """
        prompt = self._build_regenerate_steps_prompt(
            dom_html=dom_html,
            executed_steps=executed_steps,
            test_cases=test_cases,
            test_context=test_context,
            critical_fields_checklist=critical_fields_checklist,
            field_requirements=field_requirements,
            previous_paths=previous_paths,
            current_path_junctions=current_path_junctions
        )
        
        if screenshot_base64:
            content = [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/png",
                        "data": screenshot_base64
                    }
                },
                {"type": "text", "text": prompt}
            ]
            response_text = self._call_api_with_retry_multimodal(content)
        else:
            response_text = self._call_api_with_retry(prompt)
        
        if not response_text:
            return {"steps": [], "no_more_paths": False}
        
        return self._parse_steps_response(response_text)
    
    def analyze_failure_and_recover(
        self,
        failed_step: Dict,
        executed_steps: List[Dict],
        fresh_dom: str,
        screenshot_base64: Optional[str],
        test_cases: List[Dict],
        test_context: Optional[Dict],
        attempt_number: int,
        recovery_failure_history: List[Dict] = None
    ) -> List[Dict]:
        """
        Analyze step failure and generate recovery steps.
        """
        prompt = self._build_recovery_prompt(
            failed_step=failed_step,
            executed_steps=executed_steps,
            fresh_dom=fresh_dom,
            test_cases=test_cases,
            test_context=test_context,
            attempt_number=attempt_number,
            recovery_failure_history=recovery_failure_history
        )
        
        if screenshot_base64:
            content = [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/png",
                        "data": screenshot_base64
                    }
                },
                {"type": "text", "text": prompt}
            ]
            response_text = self._call_api_with_retry_multimodal(content)
        else:
            response_text = self._call_api_with_retry(prompt)
        
        if not response_text:
            return []
        
        # Extract JSON array from response
        json_match = re.search(r'\[[\s\S]*\]', response_text)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                logger.warning("[AI] Failed to parse recovery steps JSON")
                return []
        
        return []
    
    def _build_generate_steps_prompt(self, **kwargs) -> str:
        """Build prompt for initial step generation"""
        # This is a simplified version - use your full prompt from ai_form_mapper_main_prompter.py
        dom_html = kwargs.get('dom_html', '')
        test_cases = kwargs.get('test_cases', [])
        
        return f"""
# FORM MAPPER - Generate Test Steps

Analyze the following DOM and generate Selenium test steps to:
1. Fill all form fields with appropriate test data
2. Submit the form
3. Verify the submission was successful

## Test Cases:
{json.dumps(test_cases, indent=2)}

## DOM:
```html
{dom_html[:50000]}
```

## Response Format:
Return a JSON object with:
```json
{{
    "steps": [
        {{"step_number": 1, "action": "fill", "selector": "...", "value": "...", "description": "...", "test_case": "TEST_1_create_form"}},
        ...
    ],
    "no_more_paths": false
}}
```

Generate steps for ALL test cases. Return ONLY the JSON object.
"""
    
    def _build_regenerate_steps_prompt(self, **kwargs) -> str:
        """Build prompt for step regeneration after DOM change"""
        dom_html = kwargs.get('dom_html', '')
        executed_steps = kwargs.get('executed_steps', [])
        test_cases = kwargs.get('test_cases', [])
        
        return f"""
# FORM MAPPER - Regenerate Remaining Steps

The DOM has changed after executing {len(executed_steps)} steps.
Generate the REMAINING steps to complete the form.

## Already Executed Steps:
{json.dumps(executed_steps, indent=2)}

## Test Cases:
{json.dumps(test_cases, indent=2)}

## Current DOM:
```html
{dom_html[:50000]}
```

## Response Format:
Return a JSON object with only the REMAINING steps (not already executed):
```json
{{
    "steps": [
        {{"step_number": {len(executed_steps) + 1}, "action": "...", ...}},
        ...
    ],
    "no_more_paths": false
}}
```

Return ONLY the JSON object.
"""
    
    def _build_recovery_prompt(self, **kwargs) -> str:
        """Build prompt for failure recovery"""
        failed_step = kwargs.get('failed_step', {})
        executed_steps = kwargs.get('executed_steps', [])
        fresh_dom = kwargs.get('fresh_dom', '')
        test_cases = kwargs.get('test_cases', [])
        attempt_number = kwargs.get('attempt_number', 1)
        
        return f"""
# FAILURE RECOVERY

A test step has FAILED. Analyze and provide recovery steps.

## Failed Step (Attempt {attempt_number}):
{json.dumps(failed_step, indent=2)}

## Executed Steps:
{json.dumps(executed_steps[-5:], indent=2)}

## Test Cases:
{json.dumps(test_cases, indent=2)}

## Current DOM:
```html
{fresh_dom[:30000]}
```

Return a JSON array with recovery steps followed by remaining steps.
Return ONLY the JSON array.
"""
    
    def _parse_steps_response(self, response_text: str) -> Dict[str, Any]:
        """Parse AI response to extract steps"""
        try:
            # Try to parse as JSON directly
            result = json.loads(response_text)
            if isinstance(result, dict):
                return {
                    "steps": result.get("steps", []),
                    "no_more_paths": result.get("no_more_paths", False)
                }
            elif isinstance(result, list):
                return {"steps": result, "no_more_paths": False}
        except json.JSONDecodeError:
            pass
        
        # Try to extract JSON from response
        json_match = re.search(r'\{[\s\S]*\}', response_text)
        if json_match:
            try:
                result = json.loads(json_match.group())
                return {
                    "steps": result.get("steps", []),
                    "no_more_paths": result.get("no_more_paths", False)
                }
            except json.JSONDecodeError:
                pass
        
        # Try to extract array
        array_match = re.search(r'\[[\s\S]*\]', response_text)
        if array_match:
            try:
                steps = json.loads(array_match.group())
                return {"steps": steps, "no_more_paths": False}
            except json.JSONDecodeError:
                pass
        
        logger.warning("[AI] Failed to parse steps response")
        return {"steps": [], "no_more_paths": False}


# ============================================================================
# AIAlertRecoveryHelper - Alert/validation error recovery
# ============================================================================

class AIAlertRecoveryHelper(BaseAIHelper):
    """
    AI Helper for handling alerts and validation errors.
    Based on ai_form_mapper_alert_recovery_prompter.py
    """
    
    def regenerate_steps_after_alert(
        self,
        alert_info: Dict,
        executed_steps: List[Dict],
        dom_html: str,
        screenshot_base64: Optional[str],
        test_cases: List[Dict],
        test_context: Optional[Dict],
        step_where_alert_appeared: int,
        include_accept_step: bool = True,
        gathered_error_info: Optional[Dict] = None
    ) -> Optional[Dict]:
        """
        Generate steps to handle a JavaScript alert or validation error.
        
        Returns:
            Dict with 'scenario' (A or B), 'steps', 'issue_type', 'problematic_fields', etc.
        """
        prompt = self._build_alert_recovery_prompt(
            alert_info=alert_info,
            executed_steps=executed_steps,
            dom_html=dom_html,
            test_cases=test_cases,
            test_context=test_context,
            step_where_alert_appeared=step_where_alert_appeared,
            include_accept_step=include_accept_step,
            gathered_error_info=gathered_error_info
        )
        
        if screenshot_base64:
            content = [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/png",
                        "data": screenshot_base64
                    }
                },
                {"type": "text", "text": prompt}
            ]
            response_text = self._call_api_with_retry_multimodal(content)
        else:
            response_text = self._call_api_with_retry(prompt)
        
        if not response_text:
            return None
        
        return self._parse_alert_response(response_text)
    
    def _build_alert_recovery_prompt(self, **kwargs) -> str:
        """Build prompt for alert recovery"""
        alert_info = kwargs.get('alert_info', {})
        executed_steps = kwargs.get('executed_steps', [])
        dom_html = kwargs.get('dom_html', '')
        test_cases = kwargs.get('test_cases', [])
        step_where_alert_appeared = kwargs.get('step_where_alert_appeared', 0)
        gathered_error_info = kwargs.get('gathered_error_info', {})
        
        alert_text = alert_info.get('alert_text', '')
        alert_type = alert_info.get('alert_type', 'alert')
        
        error_info_section = ""
        if gathered_error_info:
            error_info_section = f"""
## Validation Errors from DOM:
- Error fields: {gathered_error_info.get('error_fields', [])}
- Error messages: {gathered_error_info.get('error_messages', [])}
"""
        
        return f"""
# ALERT/VALIDATION ERROR RECOVERY

An alert appeared after step {step_where_alert_appeared}.

## Alert Info:
- Type: {alert_type}
- Text: {alert_text}
{error_info_section}

## Executed Steps:
{json.dumps(executed_steps[-10:], indent=2)}

## Test Cases:
{json.dumps(test_cases, indent=2)}

## Current DOM:
```html
{dom_html[:40000]}
```

## Your Task:
Determine if this is:
- Scenario A: Simple confirmation alert (just continue)
- Scenario B: Validation error (need to fix fields and retry)

## Response Format:
```json
{{
    "scenario": "A" or "B",
    "issue_type": "ai_issue" or "real_issue",
    "explanation": "...",
    "problematic_fields": ["field1", "field2"],
    "field_requirements": "Clear requirements for each field",
    "steps": [...]
}}
```

Return ONLY the JSON object.
"""
    
    def _parse_alert_response(self, response_text: str) -> Optional[Dict]:
        """Parse alert recovery response"""
        # Clean up markdown code blocks
        response_text = response_text.strip()
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.startswith("```"):
            response_text = response_text[3:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
        response_text = response_text.strip()
        
        try:
            return json.loads(response_text)
        except json.JSONDecodeError:
            # Try to extract JSON object
            json_match = re.search(r'\{[\s\S]*\}', response_text)
            if json_match:
                try:
                    return json.loads(json_match.group())
                except json.JSONDecodeError:
                    pass
        
        logger.warning("[AI] Failed to parse alert response")
        return None


# ============================================================================
# AIFormPageEndPrompter - Assign test cases to steps
# ============================================================================

class AIFormPageEndPrompter(BaseAIHelper):
    """
    AI Helper for assigning test_case field to completed stages.
    Based on ai_form_mapper_end_prompter.py
    """
    
    def assign_test_cases(
        self, 
        stages: List[Dict], 
        test_cases: List[Dict]
    ) -> List[Dict]:
        """
        Assign test_case field to each stage.
        """
        prompt = f"""
You are a test automation assistant. Assign the correct test_case field to each stage.

## Test Cases:
{json.dumps(test_cases, indent=2)}

## Stages (to be updated):
{json.dumps(stages, indent=2)}

## Your Task:
For each stage, determine which test case it belongs to and update the "test_case" field.

**Rules:**
- Stages for creating/filling the form → assign to TEST_1 (or first test)
- Stages for verifying in list → assign to TEST_2
- Stages for viewing/editing → assign to TEST_3 (or appropriate test)
- Use the test_id from test_cases exactly as shown

Return ONLY the updated stages array as valid JSON.
"""
        
        response_text = self._call_api_with_retry(prompt, max_tokens=20000)
        
        if not response_text:
            return stages
        
        # Extract JSON array
        json_match = re.search(r'\[[\s\S]*\]', response_text)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass
        
        logger.warning("[AI] Failed to parse test case assignment response")
        return stages


# ============================================================================
# AIUIVisualVerifier - UI visual defect detection
# ============================================================================

class AIUIVisualVerifier(BaseAIHelper):
    """
    AI Helper for visual UI verification.
    Based on ai_form_page_ui_visual_verify_prompter.py
    """
    
    def verify_visual_ui(
        self,
        screenshot_base64: str,
        previously_reported_issues: Optional[List[str]] = None
    ) -> str:
        """
        Verify UI visual elements by analyzing a screenshot for defects.
        
        Returns:
            String describing UI issues found, or empty string if no issues
        """
        if not screenshot_base64:
            return ""
        
        # Build previously reported issues section
        previously_reported_section = ""
        if previously_reported_issues and len(previously_reported_issues) > 0:
            issues_list = "\n".join([f"- {issue}" for issue in previously_reported_issues])
            previously_reported_section = f"""
=== PREVIOUSLY REPORTED UI ISSUES ===
You have already reported these issues:
{issues_list}

**DO NOT report these issues again!**
===============================================================================
"""
        
        prompt = f"""
You are a UI/UX quality assurance expert. Perform a visual inspection of the screenshot to detect UI defects.

{previously_reported_section}

**What to Look For:**
1. Overlapping Elements
2. Unexpected Overlays (cookie banners, chat widgets)
3. Broken Layout
4. Visual Artifacts (unexpected colored boxes, shapes)
5. Styling Defects
6. Positioning Anomalies

**Response Format:**
Return ONLY a JSON object:
```json
{{
  "ui_issue": ""
}}
```

Where `ui_issue` is:
- Empty string "" if no UI issues found
- Description of issues found (comma-separated) if issues detected

Return ONLY the JSON object.
"""
        
        content = [
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/png",
                    "data": screenshot_base64
                }
            },
            {"type": "text", "text": prompt}
        ]
        
        response_text = self._call_api_with_retry_multimodal(content, max_tokens=4000)
        
        if not response_text:
            return ""
        
        # Parse JSON
        response_text = response_text.strip()
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.startswith("```"):
            response_text = response_text[3:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
        response_text = response_text.strip()
        
        try:
            result = json.loads(response_text)
            return result.get("ui_issue", "")
        except (json.JSONDecodeError, ValueError):
            logger.warning(f"[AI] Failed to parse UI verify response")
            return ""
