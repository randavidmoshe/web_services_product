# ============================================================================
# Form Mapper - AI Helpers (Wrapper)
# ============================================================================
# This module wraps the original AI prompter classes for use in the 
# distributed Form Mapper system. It imports the full prompter implementations
# from the original files.
# ============================================================================

import logging
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

# Import the original prompter classes
# These files should be copied to the services directory
from services.ai_form_mapper_main_prompter import AIHelper
from services.ai_form_mapper_alert_recovery_prompter import AIErrorRecovery
from services.ai_form_mapper_end_prompter import AIFormPageEndPrompter
from services.ai_form_page_ui_visual_verify_prompter import AIUIVisualVerifier


class AIFormMapperHelper:
    """
    Wrapper for AI-powered form step generation.
    Delegates to the original AIHelper class.
    """
    
    def __init__(self, api_key: str):
        self.helper = AIHelper(api_key)
    
    def generate_test_steps(
        self,
        dom_html: str,
        test_cases: List[Dict[str, str]],
        previous_steps: Optional[List[Dict]] = None,
        step_where_dom_changed: Optional[int] = None,
        test_context=None,
        is_first_iteration: bool = False,
        screenshot_base64: Optional[str] = None,
        critical_fields_checklist: Optional[Dict[str, str]] = None,
        field_requirements: Optional[str] = None,
        junction_instructions: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate test steps from DOM and test cases"""
        return self.helper.generate_test_steps(
            dom_html=dom_html,
            test_cases=test_cases,
            previous_steps=previous_steps,
            step_where_dom_changed=step_where_dom_changed,
            test_context=test_context,
            is_first_iteration=is_first_iteration,
            screenshot_base64=screenshot_base64,
            critical_fields_checklist=critical_fields_checklist,
            field_requirements=field_requirements,
            junction_instructions=junction_instructions
        )
    
    def regenerate_steps(
        self,
        dom_html: str,
        executed_steps: list,
        test_cases: list,
        test_context,
        screenshot_base64: Optional[str] = None,
        critical_fields_checklist: Optional[Dict[str, str]] = None,
        field_requirements: Optional[str] = None,
        junction_instructions: Optional[str] = None
    ) -> Dict[str, Any]:
        """Regenerate remaining steps after DOM change"""
        return self.helper.regenerate_steps(
            dom_html=dom_html,
            executed_steps=executed_steps,
            test_cases=test_cases,
            test_context=test_context,
            screenshot_base64=screenshot_base64,
            critical_fields_checklist=critical_fields_checklist,
            field_requirements=field_requirements,
            junction_instructions=junction_instructions
        )

    def regenerate_verify_steps(
            self,
            dom_html: str,
            executed_steps: list,
            test_cases: list,
            test_context,
            screenshot_base64: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Regenerate verification steps after Save/Submit"""
        return self.helper.regenerate_verify_steps(
            dom_html=dom_html,
            executed_steps=executed_steps,
            test_cases=test_cases,
            test_context=test_context,
            screenshot_base64=screenshot_base64,
        )


    def analyze_failure_and_recover(
            self,
            failed_step: Dict,
            executed_steps: List[Dict],
            fresh_dom: str,
            screenshot_base64: str,
            test_cases: List[Dict],
            test_context,
            attempt_number: int,
            recovery_failure_history: List[Dict] = None,
            error_message: str = ""
    ) -> List[Dict]:
        """Analyze a failed step and generate recovery steps"""
        return self.helper.analyze_failure_and_recover(
            failed_step=failed_step,
            executed_steps=executed_steps,
            fresh_dom=fresh_dom,
            screenshot_base64=screenshot_base64,
            test_cases=test_cases,
            test_context=test_context,
            attempt_number=attempt_number,
            recovery_failure_history=recovery_failure_history,
            error_message=error_message
        )

class AIAlertRecoveryHelper:
    """
    Wrapper for AI-powered alert/error recovery.
    Delegates to the original AIErrorRecovery class.
    """
    
    def __init__(self, api_key: str):
        self.helper = AIErrorRecovery(api_key)
    
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
    ) -> List[Dict]:
        """
        Generate steps to handle a JavaScript alert/confirm/prompt OR validation errors.
        
        Args:
            alert_info: Dict with 'type' and 'text' of the alert (or validation error info)
            executed_steps: Steps completed before alert appeared
            dom_html: Current DOM HTML after alert was accepted
            screenshot_base64: screenshot_base64
            test_cases: Active test cases
            test_context: Test context
            step_where_alert_appeared: Step number that triggered the alert
            include_accept_step: Whether AI should include accept_alert step in response
            gathered_error_info: Optional dict with 'error_fields' and 'error_messages' from DOM detection
            
        Returns:
            List of steps to handle alert + continue with remaining steps
        """
        return self.helper.regenerate_steps_after_alert(
            alert_info=alert_info,
            executed_steps=executed_steps,
            dom_html=dom_html,
            screenshot_base64=screenshot_base64,
            test_cases=test_cases,
            test_context=test_context,
            step_where_alert_appeared=step_where_alert_appeared,
            include_accept_step=include_accept_step,
            gathered_error_info=gathered_error_info
        )


class AIFormPageEndPrompterWrapper:
    """
    Wrapper for AI-powered test case assignment.
    Delegates to the original AIFormPageEndPrompter class.
    """
    
    def __init__(self, api_key: str):
        self.helper = AIFormPageEndPrompter(api_key)
    
    def organize_stages(
        self,
        stages: List[Dict],
        test_cases: List[Dict]
    ) -> List[Dict]:
        """
        Assign test_case field to each stage.
        
        Args:
            stages: List of stage dicts (each stage should have "test_case": "" field)
            test_cases: List of test case dicts
            
        Returns:
            Updated stages list with test_case assigned
        """
        return self.helper.organize_stages(
            stages=stages,
            test_cases=test_cases
        )


class AIUIVisualVerifierWrapper:
    """
    Wrapper for AI-powered UI visual verification.
    Delegates to the original AIUIVisualVerifier class.
    """
    
    def __init__(self, api_key: str):
        self.helper = AIUIVisualVerifier(api_key)
    
    def verify_visual_ui(
        self,
        screenshot_base64: str,
        previously_reported_issues: Optional[List[str]] = None
    ) -> str:
        """
        Verify UI visual elements by analyzing a screenshot for defects.
        
        Args:
            screenshot_base64: Base64 encoded screenshot image
            previously_reported_issues: List of issues already reported (to avoid duplicates)
            
        Returns:
            String describing UI issues found, or empty string if no issues
        """
        return self.helper.verify_visual_ui(
            screenshot_base64=screenshot_base64,
            previously_reported_issues=previously_reported_issues
        )


# ============================================================================
# Factory function for creating helpers with API key
# ============================================================================

def create_ai_helpers(api_key: str) -> Dict[str, Any]:
    """
    Create all AI helper instances with the given API key.
    
    Returns:
        Dict with helper instances
    """
    return {
        "form_mapper": AIFormMapperHelper(api_key),
        "alert_recovery": AIAlertRecoveryHelper(api_key),
        "end_prompter": AIFormPageEndPrompterWrapper(api_key),
        "ui_verifier": AIUIVisualVerifierWrapper(api_key)
    }
