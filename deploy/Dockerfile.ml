# Deployment wrapper only. Files under ml/ are copied without modification.
FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/* \
    && useradd -m -u 1001 appuser
COPY ml/requirements.txt ./requirements.txt
COPY deploy/ml-constraints.txt ./constraints.txt
RUN pip install --no-cache-dir -c constraints.txt -r requirements.txt
COPY --chown=appuser:appuser ml/app/ ./app/
USER appuser
EXPOSE 8001
HEALTHCHECK --interval=15s --timeout=3s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8001/api/v1/health')" || exit 1
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
