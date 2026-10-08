"""
Single Application Launcher for AIN-AI (Sprint S9-I Addendum Directive M2 / K1)

Usage:
  python run_app.py          # Starts with production / dev ain_ai.db
  python run_app.py --demo   # Starts with isolated demo.db and banner 'ডেমো ডেটা — নমুনা'
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

REPO_ROOT = Path(__file__).resolve().parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def get_git_commit() -> str:
    try:
        res = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True)
        if res.returncode == 0 and res.stdout.strip():
            return res.stdout.strip()
    except Exception:
        pass
    return "2026.10.08-s9-hardening"


def main():
    parser = argparse.ArgumentParser(description="AIN-AI Application Server Runner")
    parser.add_argument("--demo", action="store_true", help="Run with demo.db and display demo data banner")
    parser.add_argument("--reseed", action="store_true", help="Force re-seed demo database (idempotent)")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind (default: 8000)")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload")
    args = parser.parse_args()

    commit_hash = get_git_commit()
    is_demo = args.demo or os.getenv("DEMO_MODE", "").lower() in ("true", "1")

    if is_demo:
        current_db_url = os.getenv("DATABASE_URL", "")
        if "legal_saas.db" in current_db_url.lower():
            print("\n❌ ERROR: Refusing to start demo mode on legal_saas.db! Demo mode requires isolated demo.db.\n")
            sys.exit(1)

        os.environ["DATABASE_URL"] = "sqlite:///./demo.db"
        os.environ["DEMO_MODE"] = "true"
        db_file = "demo.db"

        demo_db_path = REPO_ROOT / "demo.db"
        if args.reseed or not demo_db_path.exists():
            print("Seeding demo database demo.db with synthetic sample data...")
            from scripts.seed_demo import build_and_seed_demo_db
            build_and_seed_demo_db()
    else:
        db_file = os.path.basename(os.getenv("DATABASE_URL", "sqlite:///./ain_ai.db").replace("sqlite:///", ""))

    dev_mode = os.getenv("DEV_MODE", "true").lower() in ("true", "1")

    banner_width = 70
    print("=" * banner_width)
    print(" " * 22 + "AIN-AI APPLICATION LAUNCHER")
    print("=" * banner_width)
    print("  Module:     services.api.app.main:app")
    print(f"  Commit:     {commit_hash}")
    print(f"  DB File:    {db_file}")
    print(f"  DEV_MODE:   {dev_mode}")
    print(f"  DEMO_MODE:  {is_demo} {'[Demo Mode: FAKE_TEST_DATA / নমুনা]' if is_demo else ''}")
    print("-" * banner_width)
    print("  Active Endpoints & URLs:")
    print(f"  * Entry / Welcome:    http://{args.host}:{args.port}/")
    print(f"  * Sign In:            http://{args.host}:{args.port}/welcome")
    print(f"  * Citizen Home:       http://{args.host}:{args.port}/home")
    print(f"  * Case Folders:       http://{args.host}:{args.port}/cases")
    print(f"  * Guided Drafting:    http://{args.host}:{args.port}/draft")
    print(f"  * Citizen Intake:     http://{args.host}:{args.port}/intake")
    print(f"  * Lawyer Sharing:     http://{args.host}:{args.port}/me/sharing")
    print(f"  * Notice Upload:      http://{args.host}:{args.port}/documents/upload")
    print(f"  * Admin Center:       http://{args.host}:{args.port}/admin")
    print(f"  * System Metrics:     http://{args.host}:{args.port}/admin/system")
    print(f"  * API Documentation:  http://{args.host}:{args.port}/docs")
    print(f"  * Build Info:         http://{args.host}:{args.port}/api/v1/build")
    print("=" * banner_width)
    print("Starting Uvicorn server...\n")

    import uvicorn
    uvicorn.run("services.api.app.main:app", host=args.host, port=args.port, reload=args.reload)


if __name__ == "__main__":
    main()
