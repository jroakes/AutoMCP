"""Tests for the prompt formatter functionality."""

import unittest

from src.prompt.formatter import format_template


class TestFormatter(unittest.TestCase):
    """Test cases for the template formatter."""

    def test_simple_variable_replacement(self):
        """Test that simple variables are replaced correctly."""
        template = "Hello, {name}!"
        result = format_template(template, name="World")
        self.assertEqual(result, "Hello, World!")

    def test_multiple_variables(self):
        """Test that multiple variables are replaced correctly."""
        template = "The {color} {animal} jumped over the {object}."
        result = format_template(
            template, color="brown", animal="fox", object="lazy dog"
        )
        self.assertEqual(result, "The brown fox jumped over the lazy dog.")

    def test_repeated_variables(self):
        """Test that repeated variables are replaced correctly."""
        template = "{name} is {name}."
        result = format_template(template, name="John")
        self.assertEqual(result, "John is John.")

    def test_missing_variable(self):
        """Test that missing variables raise KeyError."""
        template = "Hello, {name}!"
        with self.assertRaises(KeyError):
            format_template(template, user="World")

    def test_embedded_braces(self):
        """Test template with embedded braces."""
        template = "This {{is}} a {variable} with braces."
        result = format_template(template, variable="test")
        self.assertEqual(result, "This {is} a test with braces.")

    def test_complex_formatting(self):
        """Test template with complex formatting options."""
        template = "Name: {name:>10}\nAge: {age:03d}\nBalance: ${balance:.2f}"
        result = format_template(template, name="Alice", age=30, balance=125.678)
        expected = "Name:      Alice\nAge: 030\nBalance: $125.68"
        self.assertEqual(result, expected)

    def test_empty_template(self):
        """Test with empty template."""
        self.assertEqual(format_template("", name="test"), "")

    def test_no_variables(self):
        """Test template with no variables."""
        template = "Hello, World!"
        self.assertEqual(format_template(template), "Hello, World!")
