FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim AS base

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /app

RUN groupadd -r flaskuser && useradd --no-log-init -r -g flaskuser flaskuser

COPY requirements.txt .
RUN uv pip install --system --no-cache-dir -r requirements.txt

COPY ./app.py .
COPY ./entrypoint.sh .
RUN chmod +x ./entrypoint.sh
RUN chown -R flaskuser:flaskuser /app

USER flaskuser

EXPOSE 4871

ENTRYPOINT ["/app/entrypoint.sh"]
