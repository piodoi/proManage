#!/bin/sh
set -eu

PYTHON_VERSION="$(python -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
PYTHON_LIB_DIR="/usr/local/lib/python${PYTHON_VERSION}"

wait_for_mysql() {
    if [ -z "${DATABASE_URL:-}" ]; then
        return 0
    fi

    if ! python - <<'PY'
import os
import sys

database_url = os.environ.get("DATABASE_URL", "")
sys.exit(0 if database_url.startswith("mysql") else 1)
PY
    then
        return 0
    fi

    echo "[entrypoint] Waiting for MySQL to accept connections..."

    while ! python - <<'PY'
import os
import socket
import sys
from urllib.parse import urlparse

database_url = os.environ["DATABASE_URL"]
if database_url.startswith("mysql://") and "+pymysql" not in database_url:
    database_url = database_url.replace("mysql://", "mysql+pymysql://", 1)

parsed = urlparse(database_url)
host = parsed.hostname or "mysql"
port = parsed.port or 3306

try:
    with socket.create_connection((host, port), timeout=5):
        sys.exit(0)
except OSError:
    sys.exit(1)
PY
    do
        echo "[entrypoint] MySQL is not ready yet at ${DATABASE_URL%%@*}@... Retrying in 2s"
        sleep 2
    done

    echo "[entrypoint] MySQL is reachable. Starting backend."
}

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
wait_for_mysql

exec "$@"