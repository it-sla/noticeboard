FROM python:3.12-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /srv
COPY requirements.txt ./
RUN pip install -r requirements.txt
COPY alembic.ini ./
COPY alembic ./alembic
COPY app ./app
RUN useradd --system --uid 10001 --home-dir /srv app \
 && mkdir -p /data/attachments && chown -R app /data
USER app
ENV ATTACHMENT_DIR=/data/attachments
EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=5s --retries=5 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=4).status==200 else 1)"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips=*"]
