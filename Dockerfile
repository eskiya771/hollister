FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1
WORKDIR /app
COPY app.py .
COPY browser_check.py requirements.txt ./
ENV PLAYWRIGHT_BROWSERS_PATH=/opt/browsers
RUN pip install --no-cache-dir -r requirements.txt && python -m playwright install --with-deps chromium
RUN useradd --uid 10001 --create-home monitor
RUN mkdir -p /data && chown monitor:monitor /data
ENV BROWSER_PROFILE_DIR=/data/browser-profile
USER monitor
CMD ["python", "app.py"]
