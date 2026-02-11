FROM python:3.11-slim

ARG HTTP_PROXY
ARG HTTPS_PROXY

RUN pip install --no-cache-dir ddgs

EXPOSE 8000

CMD ["ddgs", "serve", "--host", "0.0.0.0", "--port", "8000"]
