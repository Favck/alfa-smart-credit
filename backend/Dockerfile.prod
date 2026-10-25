FROM node:22-slim AS frontend
WORKDIR /build
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*
COPY backend/requirements*.txt ./
RUN pip install --no-cache-dir -r requirements-prod.txt \
    && useradd --uid 10001 --create-home app
COPY backend/ ./
COPY --from=frontend /build/dist ./frontend_dist
RUN python manage.py collectstatic --noinput \
    && mkdir -p /app/data && chown -R app:app /app/data
USER app
EXPOSE 8000
CMD ["sh", "production.sh"]
