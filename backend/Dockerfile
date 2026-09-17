FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /srv

# Dependencies first: application edits should not invalidate this layer.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY migrations ./migrations
COPY alembic.ini ./

RUN useradd --system --create-home --uid 1001 api
USER api

EXPOSE 8000
# Shell form on purpose: hosting platforms inject the port to listen on, and
# 8000 is only the local default.
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
