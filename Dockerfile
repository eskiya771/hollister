FROM python:3.12-slim-bookworm AS base
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 \
    HOME=/data XDG_CACHE_HOME=/data/cache XDG_CONFIG_HOME=/data/config TMPDIR=/tmp \
    PLAYWRIGHT_BROWSERS_PATH=/opt/browsers
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt && python -m playwright install --with-deps chromium \
    && chmod -R a+rX /opt/browsers && rm -rf /var/lib/apt/lists/*
RUN useradd --uid 10001 --create-home monitor \
    && mkdir -p /data/browser-profile /data/cache /data/config \
    && chown -R monitor:monitor /data
ENV BROWSER_PROFILE_DIR=/data/browser-profile
USER monitor
CMD ["python", "app.py"]

FROM base AS manual
USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
    xvfb x11vnc novnc websockify x11-utils && rm -rf /var/lib/apt/lists/*
ENV DISPLAY=:99
COPY manual_browser.py profile_lock.py test_profile_lock.py /app/
COPY app.py browser_check.py live_monitor.py stock_diagnostics.py variant_checks.py product_checks.py telegram_summary.py /app/
USER monitor
CMD ["python", "manual_browser.py"]

FROM base AS monitor
COPY app.py browser_check.py stock_diagnostics.py profile_lock.py smoke_browser.py /app/
