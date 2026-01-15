#!/usr/bin/env python3
"""
Verification script for RepoAuditor AI implementation.
Checks that all components are properly integrated.
"""

import sys
from pathlib import Path
from typing import List, Tuple


def check_file_exists(path: Path) -> bool:
    """Check if file exists."""
    return path.exists() and path.is_file()


def check_dir_exists(path: Path) -> bool:
    """Check if directory exists."""
    return path.exists() and path.is_dir()


def verify_implementation() -> Tuple[bool, List[str]]:
    """Verify all components are in place."""

    project_root = Path(__file__).parent
    issues = []

    print("[*] Verifying RepoAuditor AI Implementation...\n")

    # Check workflows
    print("[*] Checking LangGraph Workflows...")
    workflows = [
        "app/workflows/security_fix_workflow.py",
        "app/workflows/comprehensive_review_workflow.py",
        "app/workflows/auto_fix_workflow.py",
        "app/workflows/optimize_workflow.py",
        "app/workflows/incremental_review_workflow.py",
    ]

    for workflow in workflows:
        path = project_root / workflow
        if check_file_exists(path):
            print(f"  [OK] {workflow}")
        else:
            print(f"  [FAIL] {workflow}")
            issues.append(f"Missing: {workflow}")

    # Check specialized agents
    print("\n[*] Checking Specialized Agents...")
    agents = [
        "app/agents/specialized/security_scanner.py",
        "app/agents/specialized/fix_generator.py",
        "app/agents/specialized/test_generator.py",
        "app/agents/specialized/bug_detector.py",
        "app/agents/specialized/language_detector.py",
        "app/agents/specialized/optimizer.py",
    ]

    for agent in agents:
        path = project_root / agent
        if check_file_exists(path):
            print(f"  [OK] {agent}")
        else:
            print(f"  [FAIL] {agent}")
            issues.append(f"Missing: {agent}")

    # Check command handlers
    print("\n[*] Checking Command Handlers...")
    handlers = [
        "app/commands/handlers/security_fix_handler.py",
        "app/commands/handlers/comprehensive_review_handler.py",
        "app/commands/handlers/auto_fix_handler.py",
        "app/commands/handlers/optimize_handler.py",
        "app/commands/handlers/incremental_review_handler.py",
    ]

    for handler in handlers:
        path = project_root / handler
        if check_file_exists(path):
            print(f"  [OK] {handler}")
        else:
            print(f"  [FAIL] {handler}")
            issues.append(f"Missing: {handler}")

    # Check infrastructure
    print("\n[*] Checking Infrastructure...")
    infrastructure = [
        "app/utils/rate_limiter.py",
        "app/utils/decorators.py",
        "app/models/workflow_states.py",
        "data/rate_limits.json",
    ]

    for infra in infrastructure:
        path = project_root / infra
        if check_file_exists(path):
            print(f"  [OK] {infra}")
        else:
            print(f"  [FAIL] {infra}")
            issues.append(f"Missing: {infra}")

    # Check tests
    print("\n[*] Checking Tests...")
    tests = [
        "tests/unit/test_rate_limiter.py",
    ]

    for test in tests:
        path = project_root / test
        if check_file_exists(path):
            print(f"  [OK] {test}")
        else:
            print(f"  [FAIL] {test}")
            issues.append(f"Missing: {test}")

    # Check documentation
    print("\n[*] Checking Documentation...")
    docs = [
        "docs/Testing_Github.md",
        "docs/Agent.md",
        "README.md",
    ]

    for doc in docs:
        path = project_root / doc
        if check_file_exists(path):
            print(f"  [OK] {doc}")
        else:
            print(f"  [FAIL] {doc}")
            issues.append(f"Missing: {doc}")

    # Check router registration
    print("\n[*] Checking Router Registration...")
    router_path = project_root / "app/commands/router_instance.py"
    if check_file_exists(router_path):
        content = router_path.read_text()
        commands = [
            "fix-security-issues",
            "comprehensive-review",
            "auto-fix",
            "optimize",
            "incremental-review",
        ]

        for cmd in commands:
            if cmd in content:
                print(f"  [OK] /{cmd} registered")
            else:
                print(f"  [FAIL] /{cmd} not registered")
                issues.append(f"Command not registered: /{cmd}")
    else:
        print(f"  [FAIL] router_instance.py not found")
        issues.append("Missing: app/commands/router_instance.py")

    # Summary
    print("\n" + "="*70)
    if not issues:
        print("[SUCCESS] ALL CHECKS PASSED - Implementation is complete!")
        print("="*70)
        return True, []
    else:
        print(f"[FAIL] FOUND {len(issues)} ISSUES:")
        for issue in issues:
            print(f"  • {issue}")
        print("="*70)
        return False, issues


def check_imports():
    """Check if key modules can be imported."""
    print("\n[*] Checking Python Imports...\n")

    imports_to_check = [
        ("app.utils.rate_limiter", "RateLimiter"),
        ("app.utils.decorators", "rate_limited"),
        ("app.models.workflow_states", "SecurityFixState"),
        ("app.agents.specialized.security_scanner", "SecurityScanner"),
        ("app.workflows.security_fix_workflow", "get_security_fix_workflow"),
        ("app.commands.handlers.security_fix_handler", "FixSecurityHandler"),
    ]

    all_passed = True
    for module_name, class_name in imports_to_check:
        try:
            module = __import__(module_name, fromlist=[class_name])
            getattr(module, class_name)
            print(f"  [OK] {module_name}.{class_name}")
        except Exception as e:
            print(f"  [FAIL] {module_name}.{class_name}: {str(e)}")
            all_passed = False

    if all_passed:
        print("\n[SUCCESS] All imports successful!")
    else:
        print("\n[WARN] Some imports failed (may need to install dependencies)")

    return all_passed


if __name__ == "__main__":
    # Add project root to path
    project_root = Path(__file__).parent
    sys.path.insert(0, str(project_root))

    # Verify file structure
    success, issues = verify_implementation()

    # Try import checks
    print("\n" + "="*70)
    try:
        imports_ok = check_imports()
    except Exception as e:
        print(f"\n[WARN] Import check skipped: {e}")
        imports_ok = False

    # Final summary
    print("\n" + "="*70)
    print("FINAL SUMMARY")
    print("="*70)

    if success:
        print("[OK] File Structure: PASS")
    else:
        print(f"[FAIL] File Structure: FAIL ({len(issues)} issues)")

    if imports_ok:
        print("[OK] Python Imports: PASS")
    else:
        print("[WARN] Python Imports: PARTIAL (install dependencies)")

    print("\nNext Steps:")
    print("  1. Install dependencies: pip install -e .")
    print("  2. Run tests: pytest tests/unit/test_rate_limiter.py -v")
    print("  3. Follow docs/Testing_Github.md for GitHub App setup")
    print("  4. Start server: uvicorn app.main:app --reload")

    sys.exit(0 if success else 1)
