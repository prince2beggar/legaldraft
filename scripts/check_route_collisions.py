import re
import sys
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.list_app_routes import extract_routes
from services.api.app.main import app


def check_collisions():
    routes = extract_routes(app)
    pattern_map = defaultdict(list)

    for method, path, module, name, ep in routes:
        # Standardize path: remove trailing slash, replace {param} with {}
        clean_path = path.rstrip("/") if path != "/" else "/"
        normalized = re.sub(r"\{[a-zA-Z0-9_]+\}", "{}", clean_path)
        pattern_map[(method, normalized)].append((path, module, name, ep))

    # A collision occurs when two distinct handlers or endpoints compete for the same method + path pattern
    collisions = {
        k: v for k, v in pattern_map.items() if len({(item[1], item[2]) for item in v}) > 1
    }

    print(f"Total checked endpoints: {len(routes)}")
    print(f"Total unique (method, pattern): {len(pattern_map)}")
    print(f"Total collisions detected: {len(collisions)}")

    for (m, p), handlers in collisions.items():
        print(f"\n[COLLISION] {m} {p}")
        for orig_path, mod, name in handlers:
            print(f"   -> {orig_path:45} [{mod}] {name}")

    return len(collisions)


if __name__ == "__main__":
    count = check_collisions()
    sys.exit(count)
