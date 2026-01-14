"""Test generator agent.

Generates test cases for fixes and code changes.
"""

from typing import List, Dict, Any
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class TestGenerator:
    """Generates test cases for fixes and new code."""

    def __init__(self, gemini_client: Any = None):
        """Initialize test generator."""
        self.gemini_client = gemini_client

        self.framework_map = {
            "python": "pytest",
            "javascript": "jest",
            "typescript": "jest",
            "go": "testing",
            "rust": "cargo test",
        }

    async def generate_tests(
        self,
        fix: Dict[str, Any],
        language: str = "python",
        coverage_target: float = 0.8,
    ) -> List[Dict[str, Any]]:
        """
        Generate test cases for a fix.

        Args:
            fix: ProposedFix dictionary
            language: Programming language
            coverage_target: Target code coverage (0.0-1.0)

        Returns:
            List of GeneratedTest dictionaries
        """
        logger.info(f"Generating tests for fix {fix['issue_id']}")

        test_framework = self.framework_map.get(language, "pytest")

        # Generate basic test
        tests = []

        # Test 1: Normal case
        tests.append({
            "fix_id": fix["issue_id"],
            "test_file": f"test_{fix['file'].replace('.py', '')}.py",
            "test_code": self._generate_basic_test(fix, language, test_framework),
            "test_framework": test_framework,
            "description": f"Test normal behavior after fix for {fix['issue_id']}",
        })

        # Test 2: Edge case
        tests.append({
            "fix_id": fix["issue_id"],
            "test_file": f"test_{fix['file'].replace('.py', '')}.py",
            "test_code": self._generate_edge_case_test(fix, language, test_framework),
            "test_framework": test_framework,
            "description": f"Test edge cases after fix for {fix['issue_id']}",
        })

        logger.info(f"Generated {len(tests)} test cases")

        return tests

    def _generate_basic_test(
        self, fix: Dict[str, Any], language: str, framework: str
    ) -> str:
        """Generate basic test case."""
        if language == "python" and framework == "pytest":
            return f"""
def test_{fix['issue_id']}_basic():
    '''Test basic functionality after fix.'''
    # Arrange
    test_input = "valid_input"

    # Act
    result = function_under_test(test_input)

    # Assert
    assert result is not None
    assert isinstance(result, expected_type)
"""
        return f"# Test for {fix['issue_id']}"

    def _generate_edge_case_test(
        self, fix: Dict[str, Any], language: str, framework: str
    ) -> str:
        """Generate edge case test."""
        if language == "python" and framework == "pytest":
            return f"""
def test_{fix['issue_id']}_edge_cases():
    '''Test edge cases after fix.'''
    # Test None input
    with pytest.raises(ValueError):
        function_under_test(None)

    # Test empty input
    result = function_under_test("")
    assert result == expected_empty_result

    # Test malicious input
    malicious_input = "'; DROP TABLE users; --"
    result = function_under_test(malicious_input)
    assert result is not None  # Should handle safely
"""
        return f"# Edge case test for {fix['issue_id']}"
