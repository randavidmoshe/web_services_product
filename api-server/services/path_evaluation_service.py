"""
Path Evaluation Service for Multi-Path Junction Discovery

This service analyzes completed paths and determines:
1. If more paths are needed
2. Which junction options to test next
3. Whether junctions are nested or independent
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)

# Configuration
MAX_PATHS = 7
LARGE_DROPDOWN_THRESHOLD = 10
HEURISTIC_TESTS_BEFORE_SKIP = 3
MAX_OPTIONS_FOR_JUNCTION = 8      # Skip junction if more than this many options
MAX_OPTIONS_TO_TEST = 4           # Test max this many options per junction


class JunctionStatus(Enum):
    UNKNOWN = "unknown"      # Just detected, not tested yet
    UNCERTAIN = "uncertain"  # Tested but no field change yet, need more tests
    CONFIRMED = "confirmed"  # At least one option revealed new fields
    NOT_JUNCTION = "not_junction"  # All tested options showed no field change


@dataclass
class JunctionOption:
    """Represents a single option in a junction field."""
    name: str
    tested: bool = False
    revealed_fields: Optional[bool] = None  # None=untested, True=yes, False=no


@dataclass
class Junction:
    """Represents a junction field in the form."""
    id: str
    selector: str
    junction_type: str  # "dropdown", "radio", "checkbox_group"
    step_index: int
    options: Dict[str, JunctionOption] = field(default_factory=dict)
    status: JunctionStatus = JunctionStatus.UNKNOWN
    parent_junction_id: Optional[str] = None
    parent_option: Optional[str] = None  # Which parent option reveals this junction
    
    def get_untested_options(self) -> List[str]:
        """Get list of options that haven't been tested yet."""
        return [name for name, opt in self.options.items() if not opt.tested]
    
    def get_tested_count(self) -> int:
        """Get count of tested options."""
        return sum(1 for opt in self.options.values() if opt.tested)
    
    def has_confirmed_reveal(self) -> bool:
        """Check if any option has revealed fields."""
        return any(opt.revealed_fields == True for opt in self.options.values())
    
    def all_tested_no_reveal(self) -> bool:
        """Check if all options tested and none revealed fields."""
        if not self.options:
            return False
        return all(opt.tested and opt.revealed_fields == False for opt in self.options.values())


@dataclass 
class PathResult:
    """Represents a completed path through the form."""
    path_number: int
    junction_choices: Dict[str, str]  # junction_id -> chosen_option
    junction_steps: List[Dict[str, Any]] = field(default_factory=list)  # Ordered junction steps
    result_id: Optional[int] = None  # FormMapResult ID


@dataclass
class JunctionsState:
    """Complete state of junction discovery."""
    junctions: Dict[str, Junction] = field(default_factory=dict)
    paths_completed: List[PathResult] = field(default_factory=list)
    current_path: int = 1
    
    def to_dict(self) -> Dict:
        """Serialize to dictionary for storage."""
        return {
            "junctions": {
                jid: {
                    "id": j.id,
                    "selector": j.selector,
                    "junction_type": j.junction_type,
                    "step_index": j.step_index,
                    "options": {
                        name: {
                            "name": opt.name,
                            "tested": opt.tested,
                            "revealed_fields": opt.revealed_fields
                        }
                        for name, opt in j.options.items()
                    },
                    "status": j.status.value,
                    "parent_junction_id": j.parent_junction_id,
                    "parent_option": j.parent_option
                }
                for jid, j in self.junctions.items()
            },
            "paths_completed": [
                {
                    "path_number": p.path_number,
                    "junction_choices": p.junction_choices,
                    "junction_steps": p.junction_steps,
                    "result_id": p.result_id
                }
                for p in self.paths_completed
            ],
            "current_path": self.current_path
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'JunctionsState':
        """Deserialize from dictionary."""
        state = cls()
        
        for jid, jdata in data.get("junctions", {}).items():
            junction = Junction(
                id=jdata["id"],
                selector=jdata["selector"],
                junction_type=jdata["junction_type"],
                step_index=jdata["step_index"],
                status=JunctionStatus(jdata.get("status", "unknown")),
                parent_junction_id=jdata.get("parent_junction_id"),
                parent_option=jdata.get("parent_option")
            )
            for opt_name, opt_data in jdata.get("options", {}).items():
                junction.options[opt_name] = JunctionOption(
                    name=opt_data["name"],
                    tested=opt_data["tested"],
                    revealed_fields=opt_data["revealed_fields"]
                )
            state.junctions[jid] = junction

        for pdata in data.get("paths_completed", []):
            state.paths_completed.append(PathResult(
                path_number=pdata["path_number"],
                junction_choices=pdata["junction_choices"],
                junction_steps=pdata.get("junction_steps", []),
                result_id=pdata.get("result_id")
            ))
        
        state.current_path = data.get("current_path", 1)
        return state

    @classmethod
    def load_paths_from_db(cls, db, form_page_route_id: int) -> List['PathResult']:
        """
        Load completed paths from FormMapResult table.
        Extracts junction steps from full steps for each path.

        This is the SCALABLE approach - single source of truth in DB.
        """
        from models.form_mapper_models import FormMapResult

        results = db.query(FormMapResult).filter(
            FormMapResult.form_page_route_id == form_page_route_id
        ).order_by(FormMapResult.path_number).all()

        paths = []
        for result in results:
            steps = result.steps or []

            # Extract junction steps from full steps
            junction_steps = []
            junction_choices = {}

            for step in steps:
                if step.get("is_junction"):
                    junction_info = step.get("junction_info", {})
                    junction_name = junction_info.get("junction_name", "unknown")
                    junction_id = f"junction_{junction_name}"
                    chosen_option = junction_info.get("chosen_option") or step.get("value")

                    junction_choices[junction_id] = chosen_option
                    junction_steps.append({
                        "step_index": step.get("step_number", 0),
                        "junction_id": junction_id,
                        "junction_name": junction_name,
                        "option": chosen_option,
                        "selector": step.get("selector", "")
                    })

            paths.append(PathResult(
                path_number=result.path_number,
                junction_choices=junction_choices,
                junction_steps=junction_steps,
                result_id=result.id
            ))

        logger.info(f"[PathEval] Loaded {len(paths)} paths from DB for form_page_route_id={form_page_route_id}")
        return paths

class PathEvaluationService:
    """Service for evaluating paths and determining next actions."""
    
    def __init__(
        self,
        max_paths: int = MAX_PATHS,
        max_options_for_junction: int = MAX_OPTIONS_FOR_JUNCTION,
        max_options_to_test: int = MAX_OPTIONS_TO_TEST
    ):
        self.max_paths = max_paths
        self.max_options_for_junction = max_options_for_junction
        self.max_options_to_test = max_options_to_test
    
    def update_junction_from_step(
        self,
        state: JunctionsState,
        step: Dict,
        fields_changed: bool
    ) -> JunctionsState:
        """
        Update junction state after executing a junction step.
        
        Args:
            state: Current junctions state
            step: The executed step (with is_junction and junction_info)
            fields_changed: Whether the step caused field changes
        
        Returns:
            Updated JunctionsState
        """
        if not step.get("is_junction"):
            return state
        
        junction_info = step.get("junction_info", {})
        selector = step.get("selector", "")
        
        # Generate junction ID from selector
        junction_id = f"junction_{junction_info.get('junction_name', 'unknown')}"
        
        # Get or create junction
        if junction_id not in state.junctions:

            # Check if too many options - skip if exceeds threshold
            all_options = [opt for opt in junction_info.get("all_options", []) if opt and str(opt).strip()]
            if len(all_options) > self.max_options_for_junction:
                logger.info(
                    f"[PathEval] !!!!!!!!! Skipping junction {junction_id} - too many options ({len(all_options)} > {self.max_options_for_junction})")
                return state

            # New junction discovered
            junction = Junction(
                id=junction_id,
                selector=selector,
                junction_type=junction_info.get("junction_type", "dropdown"),
                step_index=step.get("step_number", 0)
            )
            # Add all options (skip empty values - placeholder options)
            for opt_name in junction_info.get("all_options", []):
                if opt_name and str(opt_name).strip():
                    junction.options[opt_name] = JunctionOption(name=opt_name)
            state.junctions[junction_id] = junction
            logger.info(f"[PathEval] New junction discovered: {junction_id} with {len(junction.options)} options")
        
        junction = state.junctions[junction_id]
        chosen_option = junction_info.get("chosen_option") or step.get("value")
        
        # Update the tested option
        if chosen_option and chosen_option in junction.options:
            junction.options[chosen_option].tested = True
            junction.options[chosen_option].revealed_fields = fields_changed
            logger.info(f"[PathEval] Junction {junction_id} option '{chosen_option}' -> revealed_fields={fields_changed}")
        
        # Update junction status
        self._update_junction_status(junction)
        
        return state
    
    def _update_junction_status(self, junction: Junction) -> None:
        """Update junction confirmation status based on tested options."""
        
        # If any option revealed fields, it's confirmed
        if junction.has_confirmed_reveal():
            junction.status = JunctionStatus.CONFIRMED
            logger.info(f"[PathEval] Junction {junction.id} CONFIRMED (revealed fields)")
            return
        
        # Check heuristic for large dropdowns
        total_options = len(junction.options)
        tested_count = junction.get_tested_count()
        
        if total_options > LARGE_DROPDOWN_THRESHOLD and tested_count >= HEURISTIC_TESTS_BEFORE_SKIP:
            # Large dropdown with multiple tests showing no change
            all_no_reveal = all(
                opt.revealed_fields == False 
                for opt in junction.options.values() 
                if opt.tested
            )
            if all_no_reveal:
                junction.status = JunctionStatus.NOT_JUNCTION
                logger.info(f"[PathEval] Junction {junction.id} marked NOT_JUNCTION (heuristic: {tested_count} tests, no reveals)")
                return
        
        # If all options tested and none revealed fields
        if junction.all_tested_no_reveal():
            junction.status = JunctionStatus.NOT_JUNCTION
            logger.info(f"[PathEval] Junction {junction.id} marked NOT_JUNCTION (all tested, none revealed)")
            return
        
        # Still uncertain - has untested options
        if junction.get_untested_options():
            junction.status = JunctionStatus.UNCERTAIN
        else:
            junction.status = JunctionStatus.NOT_JUNCTION

    def complete_path(
            self,
            state: JunctionsState,
            junction_choices: Dict[str, str],
            junction_steps: List[Dict[str, Any]] = None,
            result_id: Optional[int] = None
    ) -> JunctionsState:
        """
        Record a completed path.

        Args:
            state: Current state
            junction_choices: Dict of junction_id -> chosen_option for this path
            junction_steps: Ordered list of junction steps (for in-memory tracking before DB save)
            result_id: Database ID of the FormMapResult

        Returns:
            Updated state
        """
        path_result = PathResult(
            path_number=state.current_path,
            junction_choices=junction_choices,
            junction_steps=junction_steps or [],
            result_id=result_id
        )
        state.paths_completed.append(path_result)
        state.current_path += 1

        logger.info(f"[PathEval] Path {path_result.path_number} completed with choices: {junction_choices}")
        if junction_steps:
            logger.info(f"[PathEval] Path {path_result.path_number} junction_steps: {junction_steps}")
        return state
    
    def evaluate_paths(self, state: JunctionsState) -> Dict[str, Any]:
        """
        Evaluate completed paths and determine if more paths are needed.
        
        Returns:
            {
                "all_paths_complete": bool,
                "next_path_number": int,
                "junction_instructions": Dict[str, str],  # selector -> option to choose
                "total_paths_needed": int,
                "reason": str
            }
        """
        # Get confirmed junctions only
        confirmed_junctions = [
            j for j in state.junctions.values() 
            if j.status == JunctionStatus.CONFIRMED
        ]
        
        # Get uncertain junctions (might still be junctions, need more testing)
        uncertain_junctions = [
            j for j in state.junctions.values()
            if j.status == JunctionStatus.UNCERTAIN
        ]
        
        logger.info(f"[PathEval] Evaluating: {len(confirmed_junctions)} confirmed, {len(uncertain_junctions)} uncertain junctions")
        # Detect nesting patterns from completed paths
        self.detect_nesting(state)
        
        # If no confirmed or uncertain junctions, we're done
        if not confirmed_junctions and not uncertain_junctions:
            return {
                "all_paths_complete": True,
                "next_path_number": state.current_path,
                "junction_instructions": {},
                "total_paths_needed": len(state.paths_completed),
                "reason": "No junctions found or all junctions confirmed as not-junctions"
            }
        
        # Check max paths limit
        if len(state.paths_completed) >= self.max_paths:
            return {
                "all_paths_complete": True,
                "next_path_number": state.current_path,
                "junction_instructions": {},
                "total_paths_needed": self.max_paths,
                "reason": f"Maximum paths limit ({self.max_paths}) reached"
            }
        
        # Find untested combinations
        next_instructions = self._find_next_combination(state, confirmed_junctions, uncertain_junctions)
        
        if not next_instructions:
            return {
                "all_paths_complete": True,
                "next_path_number": state.current_path,
                "junction_instructions": {},
                "total_paths_needed": len(state.paths_completed),
                "reason": "All junction combinations have been tested"
            }
        
        # Calculate total paths needed
        total_paths = self._calculate_total_paths(confirmed_junctions, uncertain_junctions)
        total_paths = min(total_paths, self.max_paths)
        
        return {
            "all_paths_complete": False,
            "next_path_number": state.current_path,
            "junction_instructions": next_instructions,
            "total_paths_needed": total_paths,
            "reason": f"Testing junction options: {next_instructions}"
        }
    
    def _find_next_combination(
        self,
        state: JunctionsState,
        confirmed_junctions: List[Junction],
        uncertain_junctions: List[Junction]
    ) -> Dict[str, str]:
        """
        Find the next untested combination of junction options.
        
        Returns:
            Dict mapping junction selector to option to choose
        """
        instructions = {}
        
        # First, handle uncertain junctions - test their untested options
        for junction in uncertain_junctions:
            if junction.get_tested_count() >= self.max_options_to_test:
                logger.info(
                    f"[PathEval] !!!!! Junction {junction.id} reached max options to test ({self.max_options_to_test}), skipping")
                continue
            untested = junction.get_untested_options()
            if untested:
                instructions[junction.selector] = untested[0]
                logger.info(f"[PathEval] Testing uncertain junction {junction.id} option: {untested[0]}")
                # For uncertain junctions, test one at a time
                return instructions
        
        # Then, handle confirmed junctions - find untested option combinations
        for junction in confirmed_junctions:
            if junction.get_tested_count() >= self.max_options_to_test:
                logger.info(
                    f"[PathEval] !!!!!!  Junction {junction.id} reached max options to test ({self.max_options_to_test}), skipping")
                continue
            untested = junction.get_untested_options()
            if untested:
                instructions[junction.selector] = untested[0]
                logger.info(f"[PathEval] Testing confirmed junction {junction.id} option: {untested[0]}")

                # Walk up the parent chain and add all parent junction instructions
                current = junction
                visited = set()
                while current.parent_junction_id and current.parent_option:
                    if current.parent_junction_id in visited:
                        break  # Prevent infinite loop
                    visited.add(current.parent_junction_id)
                    parent_junction = state.junctions.get(current.parent_junction_id)
                    if parent_junction:
                        instructions[parent_junction.selector] = current.parent_option
                        logger.info(
                            f"[PathEval] Adding parent junction {parent_junction.id} option: {current.parent_option}")
                        current = parent_junction
                    else:
                        break
        
        return instructions
    
    def _calculate_total_paths(
        self,
        confirmed_junctions: List[Junction],
        uncertain_junctions: List[Junction]
    ) -> int:
        """
        Calculate total paths needed based on junction structure.
        
        For now, simplified calculation:
        - Each confirmed junction with N options needs N paths total
        - Uncertain junctions need testing
        """
        if not confirmed_junctions and not uncertain_junctions:
            return 1
        
        # Simple calculation: sum of options that revealed fields + uncertain options
        total = 1  # Base path
        
        for junction in confirmed_junctions:
            options_that_reveal = sum(
                1 for opt in junction.options.values()
                if opt.revealed_fields == True
            )
            untested = len(junction.get_untested_options())
            total += options_that_reveal + untested - 1  # -1 because first path already counted
        
        for junction in uncertain_junctions:
            total += len(junction.get_untested_options())
        
        return max(1, total)

    def detect_nesting(self, state: JunctionsState) -> None:
        """
        Analyze paths to detect nested junctions using junction_steps order.

        A junction B is nested under junction A if:
        1. B only appears in paths where A has a specific option selected
        2. B appears AFTER A in the step order

        This uses junction_steps from completed paths for accurate detection.
        """
        if len(state.paths_completed) < 2:
            return

        # Build map: junction_id -> set of paths where it was used
        junction_paths: Dict[str, set] = {}
        for path in state.paths_completed:
            for jid in path.junction_choices.keys():
                if jid not in junction_paths:
                    junction_paths[jid] = set()
                junction_paths[jid].add(path.path_number)

        # Check for nesting patterns
        for jid_b, paths_b in junction_paths.items():
            if jid_b not in state.junctions:
                continue
            junction_b = state.junctions[jid_b]

            # Skip if already has parent assigned
            if junction_b.parent_junction_id:
                continue

            for jid_a, paths_a in junction_paths.items():
                if jid_a == jid_b or jid_a not in state.junctions:
                    continue

                # If B only appears in a subset of A's paths, B might be nested
                if paths_b < paths_a:  # B's paths are strict subset of A's
                    # Use junction_steps to verify order and find parent option
                    for path in state.paths_completed:
                        if path.path_number not in paths_b:
                            continue

                        # Find both junctions in the steps
                        step_a = None
                        step_b = None
                        for js in path.junction_steps:
                            if js.get("junction_id") == jid_a:
                                step_a = js
                            elif js.get("junction_id") == jid_b:
                                step_b = js

                        # Verify A comes before B in step order
                        if step_a and step_b:
                            if step_a.get("step_index", 0) < step_b.get("step_index", 0):
                                parent_option = step_a.get("option")
                                junction_b.parent_junction_id = jid_a
                                junction_b.parent_option = parent_option
                                logger.info(
                                    f"[PathEval] Detected nesting: {jid_b} (step {step_b.get('step_index')}) "
                                    f"nested under {jid_a} (step {step_a.get('step_index')}) option '{parent_option}'"
                                )
                                break

                    # Exit inner loop if parent found
                    if junction_b.parent_junction_id:
                        break


# Helper function for easy import
def create_path_evaluation_service(config: Dict = None) -> PathEvaluationService:
    """Factory function to create PathEvaluationService instance."""
    config = config or {}
    return PathEvaluationService(
        max_paths=config.get("max_junction_paths", MAX_PATHS),
        max_options_for_junction=config.get("max_options_for_junction", MAX_OPTIONS_FOR_JUNCTION),
        max_options_to_test=config.get("max_options_to_test", MAX_OPTIONS_TO_TEST)
    )
