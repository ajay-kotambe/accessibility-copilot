# Single-stage image: Chromium (downloaded below) must live in the SAME image
# Django runs from. Railpack/Railway's builder carries only whitelisted paths
# (/app/.venv, /app) from a custom build step into the deploy image, which is
# why browsers installed via a buildCommand vanished at runtime. A Dockerfile
# is deployed as-is, so nothing is dropped.
FROM python:3.13-slim

# Stable browser location, identical at build and runtime (Railway's own
# Playwright guide uses /ms-playwright). Must be set BEFORE install runs.
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
# The pip-installed playwright package downloads exactly the Chromium revision
# its driver expects (playwright==1.63.0 -> chromium v1243), so build-time
# install and runtime launch can never disagree on the revision.
# --with-deps also bakes the required system libraries into this same image.
RUN pip install --no-cache-dir -r requirements.txt \
 && python -m playwright install --with-deps chromium

COPY . .

# Railway executes a custom start command WITHOUT a shell, so a bare $PORT
# reaches gunicorn literally ("'$PORT' is not a valid port number").
# sh -c guarantees expansion whether this CMD or railway.json's identical
# startCommand is used.
CMD ["sh", "-c", "gunicorn config.wsgi:application --bind 0.0.0.0:${PORT} --workers 1 --threads 2 --timeout 300"]
