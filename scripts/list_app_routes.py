import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from services.api.app.main import app


def extract_routes(router_obj, prefix=""):
    routes_list = []
    routes = getattr(router_obj, "routes", [])
    for r in routes:
        r_type = type(r).__name__
        if r_type == "_IncludedRouter":
            inc_ctx = getattr(r, "include_context", None)
            inc_prefix = getattr(inc_ctx, "prefix", "") if inc_ctx else ""
            inc_router = getattr(inc_ctx, "included_router", getattr(r, "original_router", None))
            sub_prefix = prefix + inc_prefix
            routes_list.extend(extract_routes(inc_router, sub_prefix))
        elif hasattr(r, "methods") and hasattr(r, "path"):
            full_path = prefix + r.path
            endpoint = getattr(r, "endpoint", None)
            module = endpoint.__module__ if endpoint else "unknown"
            name = getattr(r, "name", None)
            for m in r.methods:
                routes_list.append((m, full_path, module, name, getattr(r, "endpoint", None)))
        elif hasattr(r, "routes"):
            sub_prefix = prefix + getattr(r, "path", "")
            routes_list.extend(extract_routes(r, sub_prefix))
    return routes_list


def main():
    routes = extract_routes(app)
    print(f"Total extracted routes: {len(routes)}")
    # Print distinct paths
    paths = sorted(set(x[1] for x in routes))
    print(f"Total distinct paths: {len(paths)}")
    for m, p, mod, name, ep in sorted(routes, key=lambda x: (x[1], x[0])):
        print(f"{m:7} {p:55} [{mod}] {name}")


if __name__ == "__main__":
    main()
