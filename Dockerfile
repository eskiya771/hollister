FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1
WORKDIR /app
COPY app.py .
RUN useradd --uid 10001 --create-home monitor
USER monitor
CMD ["python", "app.py"]
