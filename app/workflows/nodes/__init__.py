"""Workflow nodes for LangGraph workflows.

This package contains node functions for all multi-agent workflows.

For backward compatibility, we re-export all functions from the original
nodes.py module. New specialized workflow nodes are in their respective modules
(security_nodes.py, fix_nodes.py, etc.).
"""

# Re-export all functions from the original nodes.py for backward compatibility
# This allows existing imports like "from app.workflows.nodes import start_node" to work
from app.workflows.nodes_legacy import (
    start_node,
    fetch_pr_node,
    review_code_node,
    classify_severity_node,
    post_review_node,
    check_critical_node,
    request_approval_node,
    end_node,
    generate_review_comment,
    generate_approval_request_comment,
)

__all__ = [
    # Legacy nodes for code_review_workflow
    "start_node",
    "fetch_pr_node",
    "review_code_node",
    "classify_severity_node",
    "post_review_node",
    "check_critical_node",
    "request_approval_node",
    "end_node",
    # Helper functions
    "generate_review_comment",
    "generate_approval_request_comment",
]
