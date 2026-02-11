FROM mcr.microsoft.com/playwright/python:v1.41.0-jammy

ARG HTTP_PROXY
ARG HTTPS_PROXY
ARG NO_PROXY

RUN apt-get update \
    && apt-get install -y --no-install-recommends git curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .

CMD ["python", "main.py"]
