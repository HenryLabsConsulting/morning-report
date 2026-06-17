# The pipeline. Runs once: extract, validate, transform, load, and email the
# report. In production this would be a scheduled job (cron or a cloud runbook).
FROM python:3.12-slim
WORKDIR /app

COPY pipeline/requirements.txt ./pipeline/requirements.txt
RUN pip install --no-cache-dir -r pipeline/requirements.txt

COPY pipeline/ ./pipeline/
COPY db/ ./db/

WORKDIR /app/pipeline
CMD ["python", "run.py"]
