"""Personality-tuned prompts for AI agents."""

from app.prompts.explainer_prompts import (
    EXPLAINER_SYSTEM_PROMPT,
    get_architecture_explanation_prompt,
    get_comparison_explanation_prompt,
    get_file_explanation_prompt,
    get_function_explanation_prompt,
    get_pr_diff_explanation_prompt,
)

__all__ = [
    "EXPLAINER_SYSTEM_PROMPT",
    "get_file_explanation_prompt",
    "get_function_explanation_prompt",
    "get_pr_diff_explanation_prompt",
    "get_comparison_explanation_prompt",
    "get_architecture_explanation_prompt",
]
