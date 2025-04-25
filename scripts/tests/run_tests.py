#!/usr/bin/env python

"""
AutoMCP Enhanced Test Runner

A sophisticated test runner with beautiful formatting, error handling,
and intelligent log management.

Usage:
    python run_tests.py [options]

Options:
    --verbose, -v       Verbose output with test details
    --quiet, -q         Minimal output, errors only
    --no-logs           Hide log messages during test runs
    --filter=PATTERN    Only run tests matching pattern
    --module=MODULE     Run specific module (e.g. 'test_utils' or 'documentation')
    --failfast          Stop on first failure
    --list              List available test modules without running
    --show-warnings     Show warnings (hidden by default)
    --no-color          Disable colored output
    --help, -h          Show this help message
"""

import os
import sys
import time
import unittest
import argparse
import logging
import warnings
from io import StringIO
from datetime import datetime
from contextlib import contextmanager

try:
    from colorama import init, Fore, Back, Style

    has_colorama = True
    init()
except ImportError:
    has_colorama = False

    # Fallback mock implementation
    class ColorMock:
        def __getattr__(self, name):
            return ""

    class StyleMock:
        def __getattr__(self, name):
            return ""

    Fore = ColorMock()
    Back = ColorMock()
    Style = StyleMock()


# ===== Utility Functions =====


def pluralize(count, singular, plural=None):
    """Return singular or plural form based on count."""
    if count == 1:
        return f"{count} {singular}"
    return f"{count} {plural or singular + 's'}"


def format_time(seconds):
    """Format time duration in a human-readable way."""
    if seconds < 0.001:
        return f"{seconds * 1000000:.0f}μs"
    elif seconds < 1:
        return f"{seconds * 1000:.1f}ms"
    else:
        return f"{seconds:.2f}s"


@contextmanager
def capture_logs():
    """Capture all log messages during test execution."""
    log_capture = StringIO()
    root_logger = logging.getLogger()
    original_level = root_logger.level
    original_handlers = root_logger.handlers.copy()

    # Add a handler to capture logs
    handler = logging.StreamHandler(log_capture)
    formatter = logging.Formatter("%(levelname)s: %(name)s - %(message)s")
    handler.setFormatter(formatter)
    root_logger.handlers = [handler]

    try:
        yield log_capture
    finally:
        # Restore original handlers
        root_logger.handlers = original_handlers
        root_logger.level = original_level


# ===== Custom Test Result & Runner =====


class EnhancedTestResult(unittest.TextTestResult):
    """Enhanced test result with beautiful formatting and timing."""

    # ANSI colors and styles
    HEADER = Fore.CYAN + Style.BRIGHT if has_colorama else ""
    SUCCESS = Fore.GREEN + Style.BRIGHT if has_colorama else ""
    ERROR = Fore.RED + Style.BRIGHT if has_colorama else ""
    FAIL = Fore.RED + Style.BRIGHT if has_colorama else ""
    SKIP = Fore.YELLOW + Style.BRIGHT if has_colorama else ""
    WARNING = Fore.YELLOW if has_colorama else ""
    INFO = Fore.CYAN if has_colorama else ""
    MODULE = Fore.BLUE + Style.BRIGHT if has_colorama else ""
    DETAIL = Fore.WHITE if has_colorama else ""
    RESET = Style.RESET_ALL if has_colorama else ""

    def __init__(
        self,
        stream,
        descriptions,
        verbosity,
        show_logs=True,
        show_immediate_failures=True,
    ):
        """Initialize with additional options."""
        super().__init__(stream, descriptions, verbosity)
        self.show_logs = show_logs
        self.successes = []
        self.start_times = {}
        self.end_times = {}
        self.test_logs = {}
        self.current_module = None
        self.module_counts = {}  # Track counts by module
        self.total_tests = 0
        self.progress_dots = False  # Whether to show progress dots
        self.show_immediate_failures = show_immediate_failures

    def getDescription(self, test):
        """Format test description neatly."""
        doc = test.shortDescription() or "No description"
        name = str(test).split(" ")[0]
        return f"{name} - {doc}"

    def getModuleName(self, test):
        """Get the module name from the test."""
        return test.__class__.__module__

    def getClassName(self, test):
        """Get the class name from the test."""
        return test.__class__.__name__

    def startTest(self, test):
        """Record start time and handle module headers."""
        # Do not call super().startTest(test) to avoid progress dots
        self.start_times[test] = time.time()

        # Check if we're in a new module
        module_name = self.getModuleName(test)

        # Initialize module counts if needed
        if module_name not in self.module_counts:
            self.module_counts[module_name] = {
                "total": 0,
                "success": 0,
                "fail": 0,
                "error": 0,
                "skip": 0,
            }

        # Increment module test count
        self.module_counts[module_name]["total"] += 1
        self.total_tests += 1

        # Print module header if this is a new module
        if self.current_module != module_name and self.showAll:
            if self.current_module:
                self.stream.writeln("")  # Add spacing between modules

            self.current_module = module_name
            header = f"{self.MODULE}Module: {module_name}{self.RESET}"
            self.stream.writeln(header)

        # Print test info
        if self.showAll:
            class_name = self.getClassName(test)
            test_name = test._testMethodName
            self.stream.write(f"  {class_name}.{test_name} ... ")
            self.stream.flush()
        elif self.progress_dots:
            # This is the default unittest behavior, but we suppress it by default
            self.stream.write(".")
            self.stream.flush()

    def addSuccess(self, test):
        """Handle successful tests."""
        # Call parent but do not write dots in non-verbose mode
        self.successes.append(test)
        self.end_times[test] = time.time()

        module_name = self.getModuleName(test)
        self.module_counts[module_name]["success"] += 1

        if self.showAll:
            duration = self.end_times[test] - self.start_times[test]
            self.stream.writeln(
                f"{self.SUCCESS}PASS{self.RESET} ({format_time(duration)})"
            )

    def addError(self, test, err):
        """Handle test errors with improved formatting."""
        # Add to parent's storage but don't write to stream
        self.errors.append((test, self._exc_info_to_string(err, test)))
        self.end_times[test] = time.time()

        module_name = self.getModuleName(test)
        self.module_counts[module_name]["error"] += 1

        if self.showAll:
            duration = self.end_times[test] - self.start_times[test]
            self.stream.writeln(
                f"{self.ERROR}ERROR{self.RESET} ({format_time(duration)})"
            )
        elif self.progress_dots:
            self.stream.write("E")
            self.stream.flush()

    def addFailure(self, test, err):
        """Handle test failures with improved formatting."""
        # Add to parent's storage but don't write to stream
        error_string = self._exc_info_to_string(err, test)
        self.failures.append((test, error_string))
        self.end_times[test] = time.time()

        module_name = self.getModuleName(test)
        self.module_counts[module_name]["fail"] += 1

        if self.showAll:
            duration = self.end_times[test] - self.start_times[test]
            self.stream.writeln(
                f"{self.FAIL}FAIL{self.RESET} ({format_time(duration)})"
            )

            # Show immediate failure details if enabled
            if self.show_immediate_failures:
                self.stream.writeln("")
                self.stream.writeln(
                    f"{self.FAIL}IMMEDIATE FAILURE DETAILS:{self.RESET}"
                )
                self.stream.writeln(f"{self.DETAIL}{'-' * 70}{self.RESET}")
                self.stream.writeln(f"{self.DETAIL}{error_string}{self.RESET}")
                self.stream.writeln(f"{self.DETAIL}{'-' * 70}{self.RESET}")
                self.stream.writeln("")
        elif self.progress_dots:
            self.stream.write("F")
            self.stream.flush()

    def addSkip(self, test, reason):
        """Handle skipped tests with improved formatting."""
        # Add to parent's storage but don't write to stream
        self.skipped.append((test, reason))
        self.end_times[test] = time.time()

        module_name = self.getModuleName(test)
        self.module_counts[module_name]["skip"] += 1

        if self.showAll:
            duration = self.end_times[test] - self.start_times[test]
            self.stream.writeln(
                f"{self.SKIP}SKIP{self.RESET} ({reason}) ({format_time(duration)})"
            )
        elif self.progress_dots:
            self.stream.write("s")
            self.stream.flush()

    def addTestLog(self, test, log_content):
        """Store logs for a test."""
        self.test_logs[test] = log_content

    def printErrorList(self, flavor, errors):
        """Print errors/failures with more helpful context."""
        if not errors:
            return

        header_color = self.ERROR if flavor == "ERROR" else self.FAIL

        self.stream.writeln("")
        self.stream.writeln(f"{header_color}{'=' * 70}{self.RESET}")
        self.stream.writeln(
            f"{header_color}{flavor} DETAILS ({len(errors)}){self.RESET}"
        )
        self.stream.writeln(f"{header_color}{'=' * 70}{self.RESET}")
        self.stream.writeln("")

        for i, (test, err) in enumerate(errors):
            module_name = self.getModuleName(test)
            class_name = self.getClassName(test)
            test_name = test._testMethodName

            # Get log capture for this test if available
            logs = self.test_logs.get(test, "")

            # Calculate test duration if available
            duration_str = ""
            if test in self.start_times and test in self.end_times:
                duration = self.end_times[test] - self.start_times[test]
                duration_str = f" ({format_time(duration)})"

            # Test header with count
            self.stream.writeln(
                f"{header_color}[{i+1}/{len(errors)}] {module_name}.{class_name}.{test_name}{self.RESET}{duration_str}"
            )
            self.stream.writeln(f"{self.DETAIL}{'-' * 70}{self.RESET}")

            # Extract test docstring for context
            doc = test.shortDescription() or "No description"
            self.stream.writeln(f"{header_color}Test: {self.RESET}{doc}")

            # Error details - split into lines for better formatting
            error_lines = err.strip().split("\n")
            if error_lines:
                self.stream.writeln(f"{header_color}Error:{self.RESET}")
                for line in error_lines:
                    if "Traceback" in line:
                        self.stream.writeln(f"{header_color}{line}{self.RESET}")
                    elif line.startswith("    "):  # Code lines
                        self.stream.writeln(f"{self.DETAIL}{line}{self.RESET}")
                    elif line.startswith("  File "):  # File references
                        parts = line.split(", ", 1)
                        if len(parts) > 1:
                            file_part = parts[0].strip()
                            line_part = parts[1].strip()
                            self.stream.writeln(
                                f"  {self.INFO}{file_part}{self.RESET}, {line_part}"
                            )
                        else:
                            self.stream.writeln(f"  {self.INFO}{line}{self.RESET}")
                    elif ":" in line and line[0].isupper():  # Exception lines
                        parts = line.split(":", 1)
                        exception_type = parts[0].strip()
                        exception_msg = parts[1].strip() if len(parts) > 1 else ""
                        self.stream.writeln(
                            f"{header_color}{exception_type}:{self.RESET} {exception_msg}"
                        )
                    else:
                        self.stream.writeln(f"{self.DETAIL}{line}{self.RESET}")

            # Show logs if available and enabled
            if logs and self.show_logs:
                self.stream.writeln("")
                self.stream.writeln(f"{self.INFO}--- Captured Logs ---{self.RESET}")
                # Only show relevant logs, not all output
                log_lines = logs.strip().split("\n")
                relevant_logs = [
                    line
                    for line in log_lines
                    if test_name in line or class_name in line or module_name in line
                ]
                if relevant_logs:
                    for line in relevant_logs[-10:]:  # Show last 10 relevant lines
                        self.stream.writeln(f"{self.DETAIL}{line}{self.RESET}")
                else:
                    # If no relevant logs found, show the last few lines
                    for line in log_lines[-5:]:
                        self.stream.writeln(f"{self.DETAIL}{line}{self.RESET}")

            self.stream.writeln("")

    def printSummary(self):
        """Print a detailed test summary by module."""
        total_time = sum(
            self.end_times[test] - self.start_times[test] for test in self.end_times
        )

        self.stream.writeln("")
        self.stream.writeln(f"{self.HEADER}{'=' * 70}{self.RESET}")
        self.stream.writeln(f"{self.HEADER}TEST SUMMARY{self.RESET}")
        self.stream.writeln(f"{self.HEADER}{'=' * 70}{self.RESET}")

        # Print module-by-module summary
        for module, counts in sorted(self.module_counts.items()):
            status = (
                self.SUCCESS
                if counts["fail"] == 0 and counts["error"] == 0
                else self.FAIL
            )

            # Build status string with counts
            status_parts = []
            if counts["success"] > 0:
                status_parts.append(
                    f"{self.SUCCESS}{pluralize(counts['success'], 'pass')}{self.RESET}"
                )
            if counts["fail"] > 0:
                status_parts.append(
                    f"{self.FAIL}{pluralize(counts['fail'], 'failure')}{self.RESET}"
                )
            if counts["error"] > 0:
                status_parts.append(
                    f"{self.ERROR}{pluralize(counts['error'], 'error')}{self.RESET}"
                )
            if counts["skip"] > 0:
                status_parts.append(
                    f"{self.SKIP}{pluralize(counts['skip'], 'skipped')}{self.RESET}"
                )

            status_str = ", ".join(status_parts)
            self.stream.writeln(
                f"{status}{module}{self.RESET}: {counts['total']} tests ({status_str})"
            )

        # Print skip reasons if there are skipped tests
        if self.skipped:
            self.stream.writeln("")
            self.stream.writeln(f"{self.SKIP}Skipped test reasons:{self.RESET}")
            skip_reasons = {}

            for test, reason in self.skipped:
                module_name = self.getModuleName(test)
                if reason not in skip_reasons:
                    skip_reasons[reason] = []
                skip_reasons[reason].append(module_name)

            for reason, modules in skip_reasons.items():
                unique_modules = sorted(set(modules))
                module_str = ", ".join(unique_modules)
                self.stream.writeln(f"  - {reason} (in {module_str})")

        # Print overall summary
        success = (
            self.testsRun - len(self.failures) - len(self.errors) - len(self.skipped)
        )
        status_parts = []

        if success > 0:
            status_parts.append(
                f"{self.SUCCESS}{pluralize(success, 'pass')}{self.RESET}"
            )
        if self.failures:
            status_parts.append(
                f"{self.FAIL}{pluralize(len(self.failures), 'failure')}{self.RESET}"
            )
        if self.errors:
            status_parts.append(
                f"{self.ERROR}{pluralize(len(self.errors), 'error')}{self.RESET}"
            )
        if self.skipped:
            status_parts.append(
                f"{self.SKIP}{pluralize(len(self.skipped), 'skipped')}{self.RESET}"
            )

        status_str = ", ".join(status_parts)

        self.stream.writeln("")
        self.stream.writeln(
            f"Ran {self.total_tests} tests in {format_time(total_time)}"
        )
        self.stream.writeln(f"Result: {status_str}")
        self.stream.writeln(f"{self.HEADER}{'=' * 70}{self.RESET}")


class EnhancedTestRunner(unittest.TextTestRunner):
    """Enhanced test runner with beautiful output and log capture."""

    def __init__(self, show_logs=True, show_immediate_failures=True, **kwargs):
        """Initialize with custom result class."""
        self.show_logs = show_logs
        self.show_immediate_failures = show_immediate_failures
        kwargs.setdefault("resultclass", EnhancedTestResult)
        super().__init__(**kwargs)

    def run(self, test):
        """Run the test suite with log capture."""
        # Print header
        self.stream.writeln("")
        self.stream.writeln(f"{Fore.CYAN}{Style.BRIGHT}{'=' * 70}{Style.RESET_ALL}")
        self.stream.writeln(
            f"{Fore.CYAN}{Style.BRIGHT}               AutoMCP Test Suite Runner{Style.RESET_ALL}"
        )
        self.stream.writeln(f"{Fore.CYAN}{Style.BRIGHT}{'=' * 70}{Style.RESET_ALL}")
        self.stream.writeln(f" Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.stream.writeln(f" Python:  {sys.version.split()[0]}")

        # Show configuration info
        config_items = []
        if self.verbosity > 1:
            config_items.append("verbose")
        if self.failfast:
            config_items.append("failfast")
        if not self.show_logs:
            config_items.append("no-logs")

        if config_items:
            self.stream.writeln(f" Config:  {', '.join(config_items)}")

        self.stream.writeln(f"{Fore.CYAN}{Style.BRIGHT}{'=' * 70}{Style.RESET_ALL}")
        self.stream.writeln(
            f"{Fore.YELLOW} Tip: Run with --help to see all options{Style.RESET_ALL}"
        )
        self.stream.writeln("")

        result = self._makeResult()
        result.show_logs = self.show_logs
        result.show_immediate_failures = self.show_immediate_failures

        # Capture stdout/stderr to prevent test output from cluttering the display
        with capture_logs() as log_capture:
            startTestRun = getattr(result, "startTestRun", None)
            if startTestRun is not None:
                startTestRun()

            try:
                test(result)
            finally:
                stopTestRun = getattr(result, "stopTestRun", None)
                if stopTestRun is not None:
                    stopTestRun()

            # Store captured logs for each test
            if hasattr(result, "addTestLog"):
                log_content = log_capture.getvalue()
                for test_case in result.failures + result.errors:
                    result.addTestLog(test_case[0], log_content)

        # Print detailed error and failure information
        if result.failures:
            result.printErrorList("FAILURE", result.failures)

        if result.errors:
            result.printErrorList("ERROR", result.errors)

        # Print summary report
        if hasattr(result, "printSummary"):
            result.printSummary()

        return result


# ===== Test Discovery and Organization =====


def discover_tests(
    start_dir="tests", pattern="test_*.py", filter_pattern=None, module=None
):
    """Discover tests with filtering capabilities."""
    # Add project root to sys.path so imports work correctly
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    # Use the absolute path to tests directory
    tests_dir = os.path.join(project_root, "tests")

    if not os.path.exists(tests_dir):
        print(
            f"{Fore.RED}Error: Test directory {tests_dir} not found.{Style.RESET_ALL}"
        )
        sys.exit(1)

    # Define target directory based on module parameter
    target_dir = tests_dir
    if module:
        # Check if it's a specific module or directory
        if module.startswith("tests."):
            # Convert dotted path to directory path
            module_path = module.replace(".", os.path.sep)
            target_dir = os.path.join(project_root, module_path)
        elif os.path.exists(os.path.join(tests_dir, module)):
            # It's a subdirectory
            target_dir = os.path.join(tests_dir, module)
        elif os.path.exists(os.path.join(tests_dir, f"{module}.py")):
            # It's a specific module file
            target_dir = tests_dir
            pattern = f"{module}.py"
        else:
            # Try with test_ prefix
            module_with_prefix = (
                f"test_{module}" if not module.startswith("test_") else module
            )
            if os.path.exists(os.path.join(tests_dir, f"{module_with_prefix}.py")):
                target_dir = tests_dir
                pattern = f"{module_with_prefix}.py"
            else:
                print(
                    f"{Fore.RED}Error: Module/directory '{module}' not found.{Style.RESET_ALL}"
                )
                sys.exit(1)

    # Discover the tests
    test_loader = unittest.defaultTestLoader
    if filter_pattern:
        # Set a name filter for the loader
        old_match = test_loader._match_path

        def match_filtered_path(path, pattern, _, filter_pattern=filter_pattern):
            if old_match(path, pattern, _):
                return filter_pattern.lower() in path.lower()
            return False

        test_loader._match_path = match_filtered_path

    test_suite = test_loader.discover(target_dir, pattern=pattern)
    return test_suite


def get_available_test_modules(start_dir=None):
    """Get a list of available test modules."""
    modules = []

    # Get the tests directory path
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
    tests_dir = os.path.join(project_root, "tests")

    if not os.path.exists(tests_dir):
        return modules

    # Find all test files and directories
    for root, dirs, files in os.walk(tests_dir):
        rel_path = os.path.relpath(root, tests_dir)

        # Skip __pycache__ and hidden directories
        dirs[:] = [d for d in dirs if not d.startswith(".") and d != "__pycache__"]

        # Add directories as modules
        if root != tests_dir and "__init__.py" in files:
            module_name = rel_path.replace(os.path.sep, ".")
            if module_name != ".":  # Skip the root directory
                modules.append(module_name)

        # Add Python files as modules
        for file in files:
            if file.startswith("test_") and file.endswith(".py"):
                module_path = os.path.join(rel_path, file[:-3])
                if module_path == ".":
                    module_path = file[:-3]
                elif module_path.startswith("."):
                    module_path = module_path[2:]  # Remove leading ./
                else:
                    module_path = module_path.replace(os.path.sep, ".")
                modules.append(module_path)

    return sorted(modules)


def list_available_tests():
    """List all available test modules."""
    # Get the tests directory path
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
    tests_dir = os.path.join(project_root, "tests")

    modules = get_available_test_modules()

    if not modules:
        print(f"{Fore.YELLOW}No test modules found in {tests_dir}{Style.RESET_ALL}")
        return

    print(f"{Fore.CYAN}{Style.BRIGHT}Available Test Modules:{Style.RESET_ALL}")
    print("")

    for module in modules:
        print(f"  {Fore.GREEN}{module}{Style.RESET_ALL}")

    print("")
    print(
        f"Run tests with: {Fore.CYAN}python scripts/tests/run_tests.py --module=<module_name>{Style.RESET_ALL}"
    )


# ===== Main Function =====


def main():
    """Main entry point for the test runner."""
    # Add project root to sys.path so imports work correctly
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    parser = argparse.ArgumentParser(
        description="AutoMCP Enhanced Test Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/tests/run_tests.py                       # Run all tests
  python scripts/tests/run_tests.py --module=test_utils   # Run utils tests only
  python scripts/tests/run_tests.py --filter=ResourceManager  # Run tests matching filter
  python scripts/tests/run_tests.py --no-logs --quiet     # Run with minimal output
  python scripts/tests/run_tests.py --list                # List available test modules
  python scripts/tests/run_tests.py --failure-detail=test_exists_method  # Show details for a specific failing test
        """,
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--quiet", "-q", action="store_true", help="Minimal output")
    parser.add_argument("--no-logs", action="store_true", help="Hide log messages")
    parser.add_argument("--show-warnings", action="store_true", help="Show warnings")
    parser.add_argument(
        "--no-immediate-fail",
        action="store_true",
        help="Do not show failure details immediately when they occur",
    )
    parser.add_argument(
        "--filter", type=str, help="Only run tests containing this string"
    )
    parser.add_argument("--module", type=str, help="Run specific module or directory")
    parser.add_argument("--failfast", action="store_true", help="Stop on first failure")
    parser.add_argument(
        "--list", action="store_true", help="List available test modules"
    )
    parser.add_argument(
        "--no-color", action="store_true", help="Disable colored output"
    )
    parser.add_argument(
        "--failure-detail",
        type=str,
        help="Show detailed information about a specific failing test (e.g., test_exists_method)",
    )

    args = parser.parse_args()

    # Handle listing test modules
    if args.list:
        list_available_tests()
        return 0

    # Filter out warnings unless specifically requested
    if not args.show_warnings:
        # Ignore all warnings
        warnings.filterwarnings("ignore")
        # Extra filter for the specific Pydantic warning
        warnings.filterwarnings("ignore", message=".*shadows an attribute in parent.*")

    # Suppress logs in stdout/stderr if requested
    if args.no_logs:
        logging.getLogger().setLevel(logging.CRITICAL)

    # Disable colors if requested or not supported
    if args.no_color and has_colorama:
        for color_obj in [Fore, Back, Style]:
            for name in dir(color_obj):
                if not name.startswith("_"):
                    setattr(color_obj, name, "")

    # Discover tests
    test_suite = discover_tests(filter_pattern=args.filter, module=args.module)

    # Determine verbosity
    if args.quiet:
        verbosity = 0
    elif args.verbose:
        verbosity = 2
    else:
        verbosity = 1

    # Run tests
    runner = EnhancedTestRunner(
        verbosity=verbosity,
        failfast=args.failfast,
        show_logs=not args.no_logs,
        show_immediate_failures=not args.no_immediate_fail,
        buffer=True,  # Capture stdout/stderr
    )

    result = runner.run(test_suite)

    # If requested, show only details for a specific failing test
    if (
        args.failure_detail
        and hasattr(result, "failures")
        and hasattr(result, "errors")
    ):
        found = False
        for flavor, error_list in [
            ("FAILURE", result.failures),
            ("ERROR", result.errors),
        ]:
            for test, err in error_list:
                if (
                    test._testMethodName == args.failure_detail
                    or args.failure_detail in test._testMethodName
                ):
                    print(
                        f"\n{Fore.CYAN}{Style.BRIGHT}Detailed information for test: {test._testMethodName}{Style.RESET_ALL}"
                    )
                    print(f"{Fore.CYAN}{Style.BRIGHT}{'-' * 70}{Style.RESET_ALL}")
                    print(f"Module: {test.__class__.__module__}")
                    print(f"Class: {test.__class__.__name__}")
                    print(
                        f"Test: {test._testMethodName} - {test.shortDescription() or 'No description'}"
                    )
                    print(f"{Fore.CYAN}{Style.BRIGHT}{'-' * 70}{Style.RESET_ALL}")
                    print(
                        f"{Fore.RED if flavor == 'FAILURE' else Fore.RED}{Style.BRIGHT}{flavor}:{Style.RESET_ALL}"
                    )
                    print(f"{err}")
                    found = True
                    break
            if found:
                break

        if not found:
            print(
                f"\n{Fore.YELLOW}No test matching '{args.failure_detail}' was found in failures or errors.{Style.RESET_ALL}"
            )

    # Return appropriate exit code
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
