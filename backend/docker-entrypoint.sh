#!/bin/sh
set -eu

PYTHON_VERSION="$(python -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
PYTHON_LIB_DIR="/usr/local/lib/python${PYTHON_VERSION}"

purge_python_cache() {
    target_dir="$1"

    if [ -d "$target_dir" ]; then
        find "$target_dir" -type d -name '__pycache__' -prune -exec rm -rf {} + 2>/dev/null || true
        find "$target_dir" -type f \( -name '*.pyc' -o -name '*.pyo' \) -delete 2>/dev/null || true
    fi
}

# Clear stale bytecode caches before imports. This avoids startup failures
# when cached .pyc files from a different or corrupted Python build are present.
purge_python_cache "/app"
purge_python_cache "$PYTHON_LIB_DIR"

mkdir -p /userdata/admin/text_patterns

exec "$@"