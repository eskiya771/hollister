FROM python:3.12-slim AS base
ENV PYTHONUNBUFFERED=1
WORKDIR /app
COPY app.py .
COPY browser_check.py profile_lock.py manual_browser.py requirements.txt ./
ENV PLAYWRIGHT_BROWSERS_PATH=/opt/browsers
RUN pip install --no-cache-dir -r requirements.txt && python -m playwright install --with-deps chromium
RUN useradd --uid 10001 --create-home monitor
RUN mkdir -p /data && chown monitor:monitor /data
ENV BROWSER_PROFILE_DIR=/data/browser-profile
USER monitor
CMD ["python", "app.py"]

FROM base AS manual
USER root
RUN apt-get update && apt-get install -y --no-install-recommends xvfb x11vnc novnc websockify x11-utils && rm -rf /var/lib/apt/lists/*
ENV DISPLAY=:99
USER monitor
CMD ["python", "manual_browser.py"]

FROM base AS monitor
