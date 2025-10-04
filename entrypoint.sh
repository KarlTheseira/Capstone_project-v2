#!/bin/sh
set -e

# optional: seed DB if your app exposes init_db()
python - <<'PY'
try:
    from app import init_db
    init_db()
    print("DB initialized/verified.")
except Exception as e:
    print(f"DB init skipped: {e}")
PY

# start Gunicorn on port 8000
exec gunicorn -b 0.0.0.0:8000 app:app --workers 2 --threads 4 --timeout 60
