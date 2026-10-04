"""
Single-command test runner for AIN-AI (Sprint S0 Definition of Done)
Runs all unit and integration tests and reports status.
"""

import subprocess
import sys


def main():
    print("=" * 60)
    print("AIN-AI — Test Runner (Definition of Done Verification)")
    print("=" * 60)

    cmd = [sys.executable, "-m", "pytest", "tests/s0", "-v", "--tb=short"]
    result = subprocess.run(cmd, check=False)

    if result.returncode == 0:
        print("\n" + "=" * 60)
        print("ALL TESTS PASSED! S0 Definition of Done Criteria Satisfied.")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("TESTS FAILED. Please review the trace above.")
        print("=" * 60)

    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
