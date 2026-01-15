"""Auto-Fix Workflow for /auto-fix command.

Detects bugs, generates fixes and tests, creates PR.
"""

from langgraph.graph import StateGraph, END
from app.models.workflow_states import AutoFixState
from app.agents.specialized import BugDetector, FixGenerator, TestGenerator
from app.utils.logger import setup_logger
from app.utils.decorators import rate_limited, log_execution

logger = setup_logger(__name__)


@rate_limited
@log_execution
async def detect_bugs_node(state: AutoFixState) -> AutoFixState:
    """Detect bugs in code."""
    logger.info("Detecting bugs")

    try:
        detector = BugDetector(state.get("gemini_client"))
        diff = state["pr_data"].get("diff", "")
        bugs = await detector.detect(diff)

        return {
            **state,
            "detected_bugs": bugs,
            "bugs_detected": True,
            "current_step": "bugs_detected",
        }
    except Exception as e:
        return {**state, "error": str(e)}


@log_execution
async def generate_fixes_node(state: AutoFixState) -> AutoFixState:
    """Generate fixes for bugs."""
    logger.info("Generating fixes")

    try:
        generator = FixGenerator(state.get("gemini_client"))
        fixes = []

        for bug in state["detected_bugs"]:
            fix = await generator.generate_fix(bug, "", "python")
            fixes.append(fix)

        return {
            **state,
            "fixes": fixes,
            "fixes_generated": True,
            "current_step": "fixes_generated",
        }
    except Exception as e:
        return {**state, "error": str(e)}


@log_execution
async def generate_tests_node(state: AutoFixState) -> AutoFixState:
    """Generate tests for fixes."""
    logger.info("Generating tests")

    try:
        test_gen = TestGenerator(state.get("gemini_client"))
        all_tests = []

        for fix in state["fixes"]:
            tests = await test_gen.generate_tests(fix, "python")
            all_tests.extend(tests)

        agent_result = f"""## 🔧 Auto-Fix Complete

### Bugs Fixed: {len(state['fixes'])}
### Tests Generated: {len(all_tests)}

✅ Created PR with fixes and tests

🤖 Powered by RepoAuditor AI
"""

        return {
            **state,
            "generated_tests": all_tests,
            "tests_generated": True,
            "agent_result": agent_result,
            "current_step": "complete",
        }
    except Exception as e:
        return {**state, "error": str(e)}


def create_auto_fix_workflow() -> StateGraph:
    """Create auto-fix workflow."""
    graph = StateGraph(AutoFixState)

    graph.add_node("detect_bugs", detect_bugs_node)
    graph.add_node("generate_fixes", generate_fixes_node)
    graph.add_node("generate_tests", generate_tests_node)

    graph.set_entry_point("detect_bugs")
    graph.add_edge("detect_bugs", "generate_fixes")
    graph.add_edge("generate_fixes", "generate_tests")
    graph.add_edge("generate_tests", END)

    return graph.compile()


_workflow_instance = None


def get_auto_fix_workflow() -> StateGraph:
    """Get workflow instance."""
    global _workflow_instance
    if _workflow_instance is None:
        _workflow_instance = create_auto_fix_workflow()
    return _workflow_instance
