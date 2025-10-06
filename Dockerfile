# Use lightweight Python image
FROM python:3.12-slim

# Environment settings
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# Install system dependencies (needed for psycopg2, wget, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev wget \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy and install Python dependencies first (better layer caching)
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt \
  && python - <<'PY'
import importlib, pkgutil, sys
print('--- Dependency verification (build-time) ---')
missing = []
for mod in ['stripe']:
  if importlib.util.find_spec(mod) is None:
    missing.append(mod)
    print(f'MISSING: {mod}')
  else:
    m = importlib.import_module(mod)
    ver = getattr(m, '__version__', 'unknown')
    print(f'OK: {mod} version {ver}')
if missing:
  print('FATAL: Required modules missing at build time ->', ', '.join(missing))
  sys.exit(42)
print('--- End dependency verification ---')
PY

# Copy application code
COPY . .

# ✅ Ensure entrypoint script is executable and uses correct line endings
RUN sed -i 's/\r$//' entrypoint.sh && chmod +x entrypoint.sh

# Create instance folder and set correct permissions (optional but safe)
RUN mkdir -p /app/instance && chmod -R 755 /app/instance

# Expose Flask/Gunicorn port
EXPOSE 8000

# Health check for Kubernetes
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s \
  CMD wget -qO- http://127.0.0.1:8000/healthz || exit 1

# ✅ Entry point to run your startup script
ENTRYPOINT ["./entrypoint.sh"]
