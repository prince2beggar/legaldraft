from pathlib import Path

repo_root = Path(__file__).resolve().parent.parent
fonts_dir = repo_root / "backend" / "app" / "static" / "fonts"
print("Fonts dir exists:", fonts_dir.exists())
if fonts_dir.exists():
    for f in fonts_dir.iterdir():
        print(f"  {f.name} ({f.stat().st_size} bytes)")
else:
    print("Fonts dir not found!")
