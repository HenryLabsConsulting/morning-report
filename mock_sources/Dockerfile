# The mock vendor APIs. Serves the committed fixtures over HTTP so the pipeline
# has something realistic to extract from with no third-party accounts.
FROM python:3.12-slim
WORKDIR /app

COPY mock_sources/requirements.txt ./mock_sources/requirements.txt
RUN pip install --no-cache-dir -r mock_sources/requirements.txt

COPY mock_sources/ ./mock_sources/

EXPOSE 8077
HEALTHCHECK --interval=5s --timeout=3s --retries=10 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8077/health')"

CMD ["python", "mock_sources/app.py"]
