#!/usr/bin/env python
import unittest
import sys
import logging
from collections import defaultdict
import time
import io
import os

# Completely suppress all logging output during tests
logging.basicConfig(level=logging.CRITICAL)
# Suppress logging from all modules used in tests
for logger_name in ['src', 'urllib3', 'dotenv', 'httpx']:
    logging.getLogger(logger_name).setLevel(logging.CRITICAL)

# Check if --quiet flag is provided
QUIET_MODE = '--quiet' in sys.argv or '-q' in sys.argv
if '--quiet' in sys.argv:
    sys.argv.remove('--quiet')
if '-q' in sys.argv:
    sys.argv.remove('-q')


class TextTestResultWithoutOutput(unittest.TextTestResult):
    """A test result class that suppresses output for successful tests"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.results_by_module = defaultdict(lambda: {'total': 0, 'errors': 0, 'failures': 0, 'skipped': 0})
        self.start_time = time.time()
        
    def addError(self, test, err):
        super().addError(test, err)
        module_name = test.__class__.__module__
        self.results_by_module[module_name]['errors'] += 1
        self.results_by_module[module_name]['total'] += 1
        
    def addFailure(self, test, err):
        super().addFailure(test, err)
        module_name = test.__class__.__module__
        self.results_by_module[module_name]['failures'] += 1
        self.results_by_module[module_name]['total'] += 1
        
    def addSuccess(self, test):
        super().addSuccess(test)
        module_name = test.__class__.__module__
        self.results_by_module[module_name]['total'] += 1
        
    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        module_name = test.__class__.__module__
        self.results_by_module[module_name]['skipped'] += 1
        self.results_by_module[module_name]['total'] += 1
        
    def printErrors(self):
        if not QUIET_MODE:
            super().printErrors()

    @property
    def elapsed_time(self):
        return time.time() - self.start_time


class SummaryTestRunner(unittest.TextTestRunner):
    """Test runner that prints results by test file"""
    
    resultclass = TextTestResultWithoutOutput
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if QUIET_MODE:
            # Capture stdout to suppress unittest's output
            self.orig_stdout = sys.stdout
            sys.stdout = io.StringIO()
        
    def run(self, test):
        result = super().run(test)
        if QUIET_MODE:
            # Restore stdout
            sys.stdout = self.orig_stdout
        self._print_summary(result)
        return result
    
    def _print_summary(self, result):
        print("\n=== Summary of Test Results ===")
        
        # Sort modules by name for consistent output
        modules = sorted(result.results_by_module.items())
        
        if modules:
            column_width = max(len(module) for module, _ in modules) + 5
            
            print(f"\n{'Module':<{column_width}} {'Total':<10} {'Passed':<10} {'Failed':<10} {'Errors':<10} {'Skipped':<10}")
            print("-" * (column_width + 50))
            
            for module_name, stats in modules:
                passed = stats['total'] - stats['failures'] - stats['errors'] - stats['skipped']
                module_display = module_name.replace('test_', '')
                print(f"{module_display:<{column_width}} {stats['total']:<10} {passed:<10} {stats['failures']:<10} {stats['errors']:<10} {stats['skipped']:<10}")
            
            print("\n=== Overall ===")
            total_tests = sum(stats['total'] for _, stats in modules)
            total_passed = total_tests - len(result.failures) - len(result.errors) - len(result.skipped)
            print(f"Ran {total_tests} tests in {result.elapsed_time:.3f}s")
            print(f"Passed: {total_passed} ({total_passed/total_tests*100:.1f}%)")
            
            if result.failures:
                print(f"Failed: {len(result.failures)}")
            if result.errors:
                print(f"Errors: {len(result.errors)}")
            if result.skipped:
                print(f"Skipped: {len(result.skipped)}")
            
        print(f"\nResult: {'SUCCESS' if result.wasSuccessful() else 'FAILURE'}")


if __name__ == "__main__":
    # Create a test loader
    loader = unittest.TestLoader()
    
    # Load tests from the 'tests' directory
    test_suite = loader.discover('tests')
    
    # Use our custom summary test runner
    verbosity = 0 if QUIET_MODE else 1
    runner = SummaryTestRunner(verbosity=verbosity)
    
    # Run the tests
    result = runner.run(test_suite)
    
    # Exit with the appropriate status code
    sys.exit(not result.wasSuccessful()) 