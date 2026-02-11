FROM python:3.11-bookworm

ARG HTTP_PROXY
ARG HTTPS_PROXY
ARG NO_PROXY
ARG http_proxy
ARG https_proxy
ARG no_proxy

ENV HTTP_PROXY=${HTTP_PROXY} \
    HTTPS_PROXY=${HTTPS_PROXY} \
    NO_PROXY=${NO_PROXY} \
    http_proxy=${http_proxy:-${HTTP_PROXY}} \
    https_proxy=${https_proxy:-${HTTPS_PROXY}} \
    no_proxy=${no_proxy:-${NO_PROXY}}

RUN set -eux; \
  apt-get update; \
  apt-get install -y --no-install-recommends \
    git \
    curl \
    build-essential \
    ca-certificates \
    gnupg; \
  rm -rf /var/lib/apt/lists/*

RUN set -eux; \
  curl -fsSL https://deb.nodesource.com/setup_22.x | bash -; \
  apt-get update; \
  apt-get install -y --no-install-recommends nodejs; \
  rm -rf /var/lib/apt/lists/*

RUN npm install -g openclaw@latest

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

RUN mkdir -p /app/workspace
WORKDIR /app/workspace

CMD ["sleep", "infinity"]
