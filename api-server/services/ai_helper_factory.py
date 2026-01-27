# services/ai_helper_factory.py
# Factory functions for AI helpers - centralized mapping type logic
# Add new mapping types here only

import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


def generate_steps_for_mapping(
        mapping_type: str,
        api_key: str,
        session_logger,
        dom_html: str,
        screenshot_base64: str,
        # Form-specific params
        test_cases: list = None,
        critical_fields_checklist: dict = None,
        field_requirements: str = None,
        junction_instructions: str = None,
        user_provided_inputs: dict = None,
        is_first_iteration: bool = True,
        # Dynamic content params
        test_case_description: str = None
) -> dict:
    """
    Factory: generates steps using the appropriate AI helper based on mapping_type.
    To add a new mapping type, add an elif block here.
    """

    if mapping_type == "dynamic_content":
        from services.ai_dynamic_content_prompter import DynamicContentAIHelper
        ai_helper = DynamicContentAIHelper(api_key, session_logger=session_logger)
        return ai_helper.generate_test_steps(
            dom_html=dom_html,
            screenshot_base64=screenshot_base64,
            test_case_description=test_case_description or ""
        )
    else:
        # Default: form mapping
        from services.form_mapper_ai_helpers import create_ai_helpers
        helpers = create_ai_helpers(api_key, session_logger=session_logger)
        ai_helper = helpers["form_mapper"]
        return ai_helper.generate_test_steps(
            dom_html=dom_html,
            test_cases=test_cases,
            screenshot_base64=screenshot_base64,
            critical_fields_checklist=critical_fields_checklist or {},
            field_requirements=field_requirements or "",
            junction_instructions=junction_instructions,
            user_provided_inputs=user_provided_inputs or {},
            is_first_iteration=is_first_iteration
        )


def verify_visual_for_mapping(
        mapping_type: str,
        api_key: str,
        session_logger,
        screenshot_base64: str,
        # Form-specific params
        previously_reported_issues: list = None,
        # Dynamic content params
        test_case_description: str = None
) -> str:
    """
    Factory: visual verification using the appropriate AI helper based on mapping_type.
    To add a new mapping type, add an elif block here.
    """

    #if mapping_type == "dynamic_content":
    #    from services.ai_dynamic_content_verify_prompter import DynamicContentVerifyHelper
    #    ai_verifier = DynamicContentVerifyHelper(api_key, session_logger=session_logger)
    #    return ai_verifier.verify_visual(
    #        screenshot_base64=screenshot_base64,
    #        test_case_description=test_case_description or ""
    #    )
    #else:
    #    # Default: form mapping
    #    from services.form_mapper_ai_helpers import create_ai_helpers
    #    helpers = create_ai_helpers(api_key, session_logger=session_logger)
    #    ai_verifier = helpers["ui_verifier"]
    #    return ai_verifier.verify_visual_ui(
    #        screenshot_base64=screenshot_base64,
    #        previously_reported_issues=previously_reported_issues
    #    )

    # Default: form mapping
    from services.form_mapper_ai_helpers import create_ai_helpers
    helpers = create_ai_helpers(api_key, session_logger=session_logger)
    ai_verifier = helpers["ui_verifier"]
    return ai_verifier.verify_visual_ui(
        screenshot_base64=screenshot_base64,
        previously_reported_issues=previously_reported_issues
    )



def regenerate_steps_for_mapping(
        mapping_type: str,
        api_key: str,
        session_logger,
        dom_html: str,
        executed_steps: list,
        screenshot_base64: str = None,
        # Form-specific params
        test_cases: list = None,
        test_context: dict = None,
        critical_fields_checklist: dict = None,
        field_requirements: str = None,
        junction_instructions: str = None,
        user_provided_inputs: dict = None,
        retry_message: str = "",
        # Dynamic content params
        test_case_description: str = None
) -> dict:
    """
    Factory: regenerates steps using the appropriate AI helper based on mapping_type.
    """

    if mapping_type == "dynamic_content":
        from services.ai_dynamic_content_prompter import DynamicContentAIHelper
        ai_helper = DynamicContentAIHelper(api_key, session_logger=session_logger)
        return ai_helper.regenerate_remaining_steps(
            dom_html=dom_html,
            executed_steps=executed_steps,
            test_case_description=test_case_description or "",
            screenshot_base64=screenshot_base64
        )
    else:
        # Default: form mapping
        from services.form_mapper_ai_helpers import create_ai_helpers
        helpers = create_ai_helpers(api_key, session_logger=session_logger)
        ai_helper = helpers["form_mapper"]
        return ai_helper.regenerate_steps(
            dom_html=dom_html,
            executed_steps=executed_steps,
            test_cases=test_cases or [],
            test_context=test_context or {},
            screenshot_base64=screenshot_base64,
            critical_fields_checklist=critical_fields_checklist or {},
            field_requirements=field_requirements or "",
            junction_instructions=junction_instructions,
            user_provided_inputs=user_provided_inputs or {},
            retry_message=retry_message
        )

def recover_from_failure_for_mapping(
        mapping_type: str,
        api_key: str,
        session_logger,
        failed_step: dict,
        executed_steps: list,
        fresh_dom: str,
        screenshot_base64: str,
        # Form-specific params
        test_cases: list = None,
        test_context: dict = None,
        attempt_number: int = 1,
        recovery_failure_history: list = None,
        error_message: str = "",
        # Dynamic content params
        test_case_description: str = None
):
    """
    Factory: recovery from failure using the appropriate AI helper based on mapping_type.
    """

    if mapping_type == "dynamic_content":
        from services.ai_dynamic_content_prompter import DynamicContentAIHelper
        ai_helper = DynamicContentAIHelper(api_key, session_logger=session_logger)
        return ai_helper.analyze_failure_and_recover(
            failed_step=failed_step,
            executed_steps=executed_steps,
            fresh_dom=fresh_dom,
            screenshot_base64=screenshot_base64,
            test_case_description=test_case_description or "",
            attempt_number=attempt_number,
            error_message=error_message
        )
    else:
        # Default: form mapping
        from services.form_mapper_ai_helpers import create_ai_helpers
        helpers = create_ai_helpers(api_key, session_logger=session_logger)
        ai_helper = helpers["form_mapper"]
        return ai_helper.analyze_failure_and_recover(
            failed_step=failed_step,
            executed_steps=executed_steps,
            fresh_dom=fresh_dom,
            screenshot_base64=screenshot_base64,
            test_cases=test_cases or [],
            test_context=test_context or {},
            attempt_number=attempt_number,
            recovery_failure_history=recovery_failure_history or [],
            error_message=error_message
        )

