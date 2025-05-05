"""Prompt handling module for AutoMCP."""

from .generator import PromptGenerator, PromptTemplate
from typing import Any

__all__ = ["PromptGenerator", "PromptTemplate"]


def format_template(template: str, **kwargs: Any) -> str:
    """Format a template string with the provided variables.

    This function provides a safe way to format prompt templates.

    Args:
        template: The template string to format.
        **kwargs: The variables to use for formatting.

    Returns:
        The formatted template string.
    """
    return template.format(**kwargs)
