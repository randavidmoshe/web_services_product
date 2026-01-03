# ============================================================================
# AI Spec Compliance Prompter
# ============================================================================
# Builds prompts for AI to compare spec documents with actual form paths
# ============================================================================

import json
from typing import Dict, List


def build_spec_compliance_prompt(
        form_page_data: Dict,
        paths_data: List[Dict],
        spec_content: str
) -> str:
    """
    Build prompt for AI to generate spec compliance report
    """

    # Format paths for the prompt
    paths_text = ""
    for path in paths_data:
        path_num = path.get('path_number', 1)
        junctions = path.get('path_junctions', [])
        steps = path.get('steps', [])

        paths_text += f"\n### Path {path_num}\n"

        if junctions:
            paths_text += f"**Junctions:** {json.dumps(junctions)}\n"

        paths_text += "**Steps:**\n"
        for i, step in enumerate(steps, 1):
            action = step.get('action', 'unknown')
            selector = step.get('selector', '')
            value = step.get('value', step.get('input_value', ''))
            description = step.get('description', '')

            step_line = f"  {i}. [{action}]"
            if selector:
                step_line += f" selector: `{selector}`"
            if value:
                step_line += f" value: `{value}`"
            if description:
                step_line += f" - {description}"
            paths_text += step_line + "\n"

    # Format navigation steps
    nav_steps_text = ""
    nav_steps = form_page_data.get('navigation_steps', [])
    if nav_steps:
        nav_steps_text = "\n**Navigation Steps to Reach Form:**\n"
        for i, step in enumerate(nav_steps, 1):
            action = step.get('action', 'unknown')
            selector = step.get('selector', '')
            value = step.get('value', '')
            description = step.get('description', step.get('name', ''))
            nav_steps_text += f"  {i}. [{action}] {description}"
            if selector:
                nav_steps_text += f" (selector: `{selector}`)"
            if value:
                nav_steps_text += f" (value: `{value}`)"
            nav_steps_text += "\n"

    prompt = f"""You are a QA compliance analyst. Your task is to compare a specification document against the actual implementation of a web form, as captured by automated test paths.

## Form Information
- **Form Name:** {form_page_data.get('form_name', 'Unknown')}
- **URL:** {form_page_data.get('url', 'Unknown')}
{nav_steps_text}

## Specification Document
```
{spec_content}
```

## Actual Implementation (Captured Paths)
{paths_text}

## Your Task

Analyze the specification document and compare it against the actual form implementation shown in the paths above. Generate a **Markdown compliance report** with the following sections:

### 1. Executive Summary
Brief overview of compliance status (X of Y requirements met)

### 2. Detailed Compliance Analysis

For EACH requirement/item in the spec, create an entry:

#### [Requirement Name/ID]
- **Spec Says:** [What the spec requires]
- **Implementation:** [What the paths show]
- **Status:** ✅ Compliant | ❌ Non-Compliant | ⚠️ Partially Compliant | ❓ Cannot Verify
- **Notes:** [Any additional observations]

### 3. Missing from Implementation
List any items in the spec that are NOT found in the paths

### 4. Extra in Implementation
List any fields/actions in the paths that are NOT mentioned in the spec

### 5. Recommendations
Suggestions for addressing any gaps

---

**Important Guidelines:**
- Be thorough - check every item in the spec
- Use the emoji status indicators consistently
- If you can't verify something from the paths, mark it as ❓
- Consider field names, actions, validations, sections, tabs, junctions
- Look for both presence AND correctness of implementation

Generate the compliance report now:"""

    return prompt