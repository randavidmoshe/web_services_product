# ============================================================================
# Form Mapper - AI Field Assist Slider Prompter
# ============================================================================
# AI queries for slider interactions during step execution.
# Generates click coordinates and reads slider values using vision.
# ============================================================================

import logging
import json
import anthropic
from typing import Dict, Any

logger = logging.getLogger(__name__)


class AIFieldAssistSliderPrompter:
    """
    AI helper for slider-specific queries during step execution.
    """

    def __init__(self, api_key: str):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = "claude-sonnet-4-20250514"

    def generate_click_points(
            self,
            rail_bounds: Dict[str, float],
            action_type: str,
            step: Dict
    ) -> Dict[str, Any]:
        """Generate click point(s) for a slider based on rail bounds."""
        selector = step.get("selector", "")
        description = step.get("description", "")

        if action_type == "range_slider":
            response_format = '{"x1": <number>, "y1": <number>, "x2": <number>, "y2": <number>}'
            point_instruction = "Generate TWO click points. Point 1 for the lower/left handle, Point 2 for the upper/right handle. Ensure at least 20% of rail length between them."
        else:
            response_format = '{"x": <number>, "y": <number>}'
            point_instruction = "Generate ONE click point at a random position along the slider rail."

        prompt = f"""Generate click coordinates for a slider.

SLIDER INFO:
- Selector: {selector}
- Description: {description}
- Action type: {action_type}
- Rail bounds (absolute pixels):
  - left: {rail_bounds['left']:.0f}
  - top: {rail_bounds['top']:.0f}
  - width: {rail_bounds['width']:.0f}
  - height: {rail_bounds['height']:.0f}

TASK:
{point_instruction}

RULES:
1. Determine orientation: HORIZONTAL if width > height, VERTICAL if height > width
2. For HORIZONTAL: X varies between left and left+width, Y = top + height/2
3. For VERTICAL: Y varies between top and top+height, X = left + width/2
4. Add 10px padding from edges
5. Return absolute pixel coordinates

Respond with ONLY valid JSON (no markdown, no explanation):
{response_format}"""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=150,
                messages=[{"role": "user", "content": prompt}]
            )
            response_text = response.content[0].text.strip()
            logger.info(f"[AIFieldAssistSlider] generate_click_points response: {response_text}")

            clean_response = response_text
            if '```json' in clean_response:
                clean_response = clean_response.split('```json')[1].split('```')[0]
            elif '```' in clean_response:
                clean_response = clean_response.split('```')[1].split('```')[0]

            result = json.loads(clean_response.strip())
            result["success"] = True
            return result

        except Exception as e:
            logger.error(f"[AIFieldAssistSlider] generate_click_points failed: {e}")
            return {"success": False, "error": str(e)}

    def read_value(self, screenshot_base64: str, action_type: str, step: Dict) -> Dict[str, Any]:
        """Read current value(s) from a slider using AI vision."""
        selector = step.get("selector", "")
        description = step.get("description", "")

        if action_type == "range_slider":
            prompt = f"""Look at this screenshot of a RANGE SLIDER (two handles).

Slider info:
- Selector: {selector}
- Description: {description}

Read the current min and max values. Look for:
- Value labels/tooltips near the handles
- Text displays showing the range
- Input fields connected to the slider

Respond with ONLY JSON (no markdown):
{{"min_value": "<lower value>", "max_value": "<higher value>"}}"""
        else:
            prompt = f"""Look at this screenshot of a SLIDER.

Slider info:
- Selector: {selector}
- Description: {description}

Read the current value. Look for:
- Value label/tooltip near the handle
- Text display showing current value
- Input field connected to the slider

Respond with ONLY JSON (no markdown):
{{"value": "<current value>"}}"""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=150,
                messages=[{"role": "user", "content": [
                    {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": screenshot_base64}},
                    {"type": "text", "text": prompt}
                ]}]
            )
            response_text = response.content[0].text.strip()
            logger.info(f"[AIFieldAssistSlider] read_value response: {response_text}")

            clean_response = response_text
            if '```json' in clean_response:
                clean_response = clean_response.split('```json')[1].split('```')[0]
            elif '```' in clean_response:
                clean_response = clean_response.split('```')[1].split('```')[0]

            result = json.loads(clean_response.strip())
            result["success"] = True
            return result

        except Exception as e:
            logger.error(f"[AIFieldAssistSlider] read_value failed: {e}")
            if action_type == "range_slider":
                return {"min_value": "unknown", "max_value": "unknown", "success": False, "error": str(e)}
            return {"value": "unknown", "success": False, "error": str(e)}