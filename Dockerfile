FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    TZ=Europe/Moscow

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates tzdata \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --upgrade pip \
    && pip install -r requirements.txt

COPY app ./app
COPY config.py ./
COPY README.md ./
COPY env_example.txt ./
COPY run_telegram_bot.py ./
COPY run_vk_bot.py ./
COPY run_vk._bot.py ./

RUN mkdir -p /app/data

CMD ["python", "-m", "app.entrypoints.all"]
