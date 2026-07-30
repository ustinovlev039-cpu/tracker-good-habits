FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt .

RUN python -m pip install --timeout=60 --retries=5 -r requirements.txt

RUN groupadd --system django \
    && useradd --system --gid django --home-dir /app django

COPY --chown=django:django . .

RUN mkdir -p /app/staticfiles /app/media /var/lib/celery \
    && chown -R django:django /app/staticfiles /app/media /var/lib/celery

USER django

EXPOSE 8000

CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--access-logfile", "-", "--error-logfile", "-"]
