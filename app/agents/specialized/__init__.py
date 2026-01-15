"""Specialized agents for multi-agent workflows.

This package contains task-specific agents that power
the LangGraph multi-agent workflow system.
"""

from app.agents.specialized.security_scanner import SecurityScanner
from app.agents.specialized.fix_generator import FixGenerator
from app.agents.specialized.test_generator import TestGenerator
from app.agents.specialized.bug_detector import BugDetector
from app.agents.specialized.language_detector import LanguageDetector
from app.agents.specialized.optimizer import Optimizer

__all__ = [
    "SecurityScanner",
    "FixGenerator",
    "TestGenerator",
    "BugDetector",
    "LanguageDetector",
    "Optimizer",
]
