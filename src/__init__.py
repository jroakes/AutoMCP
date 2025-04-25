"""
Name: AutoMCP package.
Description: Defines the package version and imports the main CLI function, establishing AutoMCP as a package for building MCP servers from OpenAPI specs. Serves as the entry point for the AutoMCP package.
"""

__version__ = "0.1.2"
__author__ = "JR Oakes"

from .main import main as cli_main

__all__ = ["cli_main"]
