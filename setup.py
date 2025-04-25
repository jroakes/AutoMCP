#!/usr/bin/env python

from setuptools import setup, find_packages
import re

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as f:
    requirements = f.read().splitlines()

# Read version from __init__.py
with open("src/__init__.py", "r", encoding="utf-8") as f:
    version_match = re.search(r'__version__ = "(.*?)"', f.read())
    version = version_match.group(1) if version_match else "0.1.0"

setup(
    name="automcp",
    version=version,
    author="JR Oakes",
    author_email="",
    description="Build MCP servers from OpenAPI specs",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/jroakes/AutoMCP",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "automcp=src.main:main",
        ],
    },
)
