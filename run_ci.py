"""
Single-command CI runner for AIN-AI (Sprint S0 Definition of Done).
Executes:
1. Linting with Ruff
2. Type checking with Mypy
3. Full test suite with Pytest (including reversible migrations and a11y)
"""

import subprocess
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


class TeeWriter:
    def __init__(self, original, file_handle):
        self.original = original
        self.file_handle = file_handle

    def write(self, text):
        self.original.write(text)
        self.file_handle.write(text)
        self.file_handle.flush()

    def flush(self):
        self.original.flush()
        self.file_handle.flush()


def run_stage(name: str, cmd: list[str]) -> bool:
    print("\n" + "=" * 65)
    print(f" CI STAGE: {name}")
    print(f" Command:  {' '.join(cmd)}")
    print("=" * 65)

    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        encoding="utf-8",
        errors="replace",
    )
    if proc.stdout:
        for line in proc.stdout:
            print(line, end="")
    proc.wait()

    if proc.returncode != 0:
        print(f"\n[FAILED] Stage '{name}' exited with code {proc.returncode}")
        return False
    print(f"\n[PASSED] Stage '{name}'")
    return True


def main():
    reports_dir = Path("reports")
    reports_dir.mkdir(parents=True, exist_ok=True)
    ci_log_path = reports_dir / "ci_latest.txt"
    log_file = open(ci_log_path, "w", encoding="utf-8")

    orig_stdout = sys.stdout
    orig_stderr = sys.stderr
    sys.stdout = TeeWriter(orig_stdout, log_file)  # type: ignore[assignment]
    sys.stderr = TeeWriter(orig_stderr, log_file)  # type: ignore[assignment]

    try:
        tests_dir = Path("tests")
        sprint_dirs = sorted(
            [d.name for d in tests_dir.iterdir() if d.is_dir() and d.name.startswith("s")]
        )
        current_sprint = sprint_dirs[-1].upper() if sprint_dirs else "S0"

        print("*" * 65)
        print(
            f"  AIN-AI Local CI Pipeline — Sprint {current_sprint} Definition of Done (S0-{current_sprint} Verified)"
        )
        print("*" * 65)

        test_targets = [f"tests/{d}" for d in sprint_dirs]

        stages = [
            ("1. Code Linting (Ruff)", [sys.executable, "-m", "ruff", "check", "."]),
            (
                "2. Static Type Checking (Mypy)",
                [
                    sys.executable,
                    "-m",
                    "mypy",
                    "packages",
                    "services",
                    "--explicit-package-bases",
                    "--ignore-missing-imports",
                    "--check-untyped-defs",
                ],
            ),
            (
                f"3. Automated Tests (Pytest S0 through {current_sprint}, Reversibility & Viewports)",
                [
                    sys.executable,
                    "-m",
                    "pytest",
                    *test_targets,
                    "-v",
                    "--tb=short",
                    "--junitxml=reports/junit_latest.xml",
                ],
            ),
            (
                "4. Rendered Text & Bangla Digit Compliance Lint",
                [sys.executable, "scripts/lint_rendered_text.py"],
            ),
            (
                "5. Screenshot Uniqueness & Route Integrity Verification",
                [sys.executable, "scripts/verify_screenshots.py", "storage/screenshots/visible_fix"],
            ),
        ]

        for stage_name, cmd in stages:
            if "5. Screenshot" in stage_name:
                visible_fix_dir = Path("storage/screenshots/visible_fix")
                if not visible_fix_dir.exists() or len(list(visible_fix_dir.glob("*.png"))) < 10:
                    print("\n[CI Stage 5 Pre-requisite] storage/screenshots/visible_fix missing or empty.")
                    print("Generating screenshots via scripts/capture_visible_fix_screenshots.py...")
                    subprocess.run([sys.executable, "scripts/capture_visible_fix_screenshots.py"], check=True)

            success = run_stage(stage_name, cmd)
            if not success:
                print("\n" + "!" * 65)
                print("[ERROR] CI PIPELINE FAILED. Please resolve errors before proceeding.")
                print("!" * 65)
                sys.exit(1)

        print("\n" + "*" * 65)
        print(f"[SUCCESS] ALL CI CHECKS PASSED! S0 THROUGH {current_sprint} SUITES GREEN.")
        print("*" * 65)
        sys.exit(0)
    finally:
        sys.stdout = orig_stdout
        sys.stderr = orig_stderr
        log_file.close()


if __name__ == "__main__":
    main()
