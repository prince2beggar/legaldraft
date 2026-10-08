from pathlib import Path

repo_root = Path(__file__).resolve().parent.parent

for f in repo_root.glob("**/*.py"):
    if "venv" in str(f) or ".git" in str(f):
        continue
    text = f.read_text(encoding="utf-8", errors="ignore")
    if "/demo" in text or "demo_login" in text:
        print(f"Found in {f.relative_to(repo_root)}")
