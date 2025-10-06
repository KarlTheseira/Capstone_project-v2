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
try:
    import importlib.util, importlib
    spec = importlib.util.find_spec('stripe')
    if spec is None:
        print('RUNTIME CHECK: stripe module NOT FOUND before gunicorn start')
    else:
        stripe = importlib.import_module('stripe')
        print('RUNTIME CHECK: stripe module present, version:', getattr(stripe, '__version__', 'unknown'))
except Exception as e:
    print('RUNTIME CHECK: Unexpected error while checking stripe:', e)
PY

# start Gunicorn on port 8000
exec gunicorn -b 0.0.0.0:8000 app:app --workers 2 --threads 4 --timeout 60
