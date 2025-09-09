import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple


class ProductionReadinessChecker:
    """
    Comprehensive production readiness validation.
    This class coordinates all tests and provides clear deployment decisions.
    """

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        # CORRECTED: Added type annotations for mypy
        self.test_results: Dict[str, Dict[str, Any]] = {}
        self.critical_failures: List[str] = []
        self.warnings: List[str] = []
        self.deployment_ready = False

    def run_all_checks(self) -> bool:
        """
        Run all production readiness checks.
        Returns True if safe to deploy, False otherwise.
        """
        print("🚀 Starting Production Readiness Assessment")
        print("=" * 60)

        test_suites = [
            ("Configuration Validation", "test_config_validation.py", True),
            ("Service Dependencies", "test_service_dependencies.py", True),
            ("Resource & Performance", "test_resource_performance.py", False),
        ]

        for suite_name, test_file, is_critical in test_suites:
            print(f"\n📋 Running {suite_name}...")
            success, output = self._run_test_suite(test_file)

            self.test_results[suite_name] = {
                "passed": success,
                "critical": is_critical,
                "output": output,
            }

            if not success:
                if is_critical:
                    self.critical_failures.append(suite_name)
                    print(f"  ❌ CRITICAL FAILURE: {suite_name}")
                else:
                    self.warnings.append(suite_name)
                    print(f"  ⚠️  WARNING: {suite_name} (non-critical)")
            else:
                print(f"  ✅ PASSED: {suite_name}")

        # Determine if ready for deployment
        self.deployment_ready = len(self.critical_failures) == 0

        # Print summary
        self._print_summary()

        return self.deployment_ready

    def _run_test_suite(self, test_file: str) -> Tuple[bool, str]:
        """Run a test suite and capture results."""
        test_path = Path(__file__).parent / "production_readiness" / test_file

        result = subprocess.run(
            [sys.executable, "-m", "pytest", str(test_path), "-v", "--tb=short"],
            capture_output=True,
            text=True,
            check=False,
        )

        success = result.returncode == 0
        output = result.stdout + result.stderr if not success else result.stdout

        if self.verbose:
            print(output)

        return success, output

    def _print_summary(self):
        """Print a comprehensive summary of the readiness assessment."""
        print("\n" + "=" * 60)
        print("📊 PRODUCTION READINESS SUMMARY")
        print("=" * 60)

        # Overall status
        if self.deployment_ready:
            print("\n✅ DEPLOYMENT READY")
            print("All critical checks passed. Safe to deploy to production.")
        else:
            print("\n❌ NOT READY FOR DEPLOYMENT")
            print("Critical issues found that WILL cause production failures.")

        # Critical failures
        if self.critical_failures:
            print("\n🚨 CRITICAL FAILURES (Must fix before deployment):")
            for failure in self.critical_failures:
                print(f"  - {failure}")
                self._print_failure_details(failure)

        # Warnings
        if self.warnings:
            print("\n⚠️  WARNINGS (Should fix but not blocking):")
            for warning in self.warnings:
                print(f"  - {warning}")

        print("\n" + "=" * 60)

    def _print_failure_details(self, suite_name: str):
        """Print specific details about what will fail in production."""
        failure_impacts = {
            "Configuration Validation": [
                "- Application won't start (immediate crash loop)",
                "- API connections will fail",
                "- No data persistence",
                "- Estimated debug time: 2-4 hours",
            ],
            "Service Dependencies": [
                "- Random failures under load",
                "- Data loss possible",
                "- Cache/session storage broken",
                "- Estimated debug time: 4-8 hours",
            ],
            "Resource & Performance": [
                "- Container killed by orchestrator",
                "- Out of memory crashes",
                "- Slow response times",
                "- Estimated debug time: 6-12 hours",
            ],
        }

        if suite_name in failure_impacts:
            print("    Production impact if deployed:")
            for impact in failure_impacts[suite_name]:
                print(f"    {impact}")

    def generate_report(self, output_file: str = "production_readiness_report.json"):
        """Generate a detailed JSON report of the assessment."""
        report = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "deployment_ready": self.deployment_ready,
            "critical_failures": self.critical_failures,
            "warnings": self.warnings,
            "test_results": self.test_results,
            "recommendation": "DEPLOY" if self.deployment_ready else "DO NOT DEPLOY",
        }

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)

        print(f"\n📄 Detailed report saved to: {output_file}")


def main():
    """Main entry point for the production readiness checker."""
    parser = argparse.ArgumentParser(
        description="Production Readiness Assessment - Your deployment safety gate"
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Show detailed test output"
    )
    parser.add_argument(
        "--report", "-r", action="store_true", help="Generate JSON report"
    )

    args = parser.parse_args()

    checker = ProductionReadinessChecker(verbose=args.verbose)

    # Run all checks
    is_ready = checker.run_all_checks()

    # Generate report if requested
    if args.report:
        checker.generate_report()

    # Exit with appropriate code
    sys.exit(0 if is_ready else 1)


if __name__ == "__main__":
    main()
