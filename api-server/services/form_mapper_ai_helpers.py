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
        previous_paths: Optional[List[Dict]] = None,
        current_path_junctions: Optional[List[Dict]] = None
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
            previous_paths=previous_paths,
            current_path_junctions=current_path_junctions
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
        previous_paths: Optional[List[Dict]] = None,
        current_path_junctions: Optional[List[Dict]] = None
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
            previous_paths=previous_paths,
            current_path_junctions=current_path_junctions
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
        dom_html: str,
        alert_text: str,
        executed_steps: list,
        test_cases: list,
        test_context,
        gathered_error_info: Optional[Dict] = None,
        screenshot_base64: Optional[str] = None,
        previous_paths: Optional[List[Dict]] = None,
        current_path_junctions: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """Analyze alert and regenerate steps for recovery"""
        return self.helper.regenerate_steps_after_alert(
            dom_html=dom_html,
            alert_text=alert_text,
            executed_steps=executed_steps,
            test_cases=test_cases,
            test_context=test_context,
            gathered_error_info=gathered_error_info,
            screenshot_base64=screenshot_base64,
            previous_paths=previous_paths,
            current_path_junctions=current_path_junctions
        )


class AIFormPageEndPrompterWrapper:
    """
    Wrapper for AI-powered test case assignment.
    Delegates to the original AIFormPageEndPrompter class.
    """
    
    def __init__(self, api_key: str):
        self.helper = AIFormPageEndPrompter(api_key)
    
    def assign_test_cases(
        self,
        steps: List[Dict],
        test_cases: List[Dict]
    ) -> List[Dict]:
        """Assign test_case field to each step"""
        return self.helper.assign_test_cases(
            steps=steps,
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
        dom_html: str,
        previously_reported_issues: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Verify UI for visual defects"""
        return self.helper.verify_visual_ui(
            screenshot_base64=screenshot_base64,
            dom_html=dom_html,
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
