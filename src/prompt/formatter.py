"""
Name: Prompt formatter.
Description: Provides utilities for safely formatting prompt templates with variables.
"""

from typing import Any


def format_template(template: str, **kwargs: Any) -> str:
    """Format a template string with the provided variables.

    This function provides a safe way to format prompt templates without using exec().

    Args:
        template: The template string to format.
        **kwargs: The variables to use for formatting.

    Returns:
        The formatted template string.
    """
    return template.format(**kwargs)
