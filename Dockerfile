FROM python:3.12-slim

# Build/runtime deps only -- no compilers needed for this project's deps.
RUN useradd --create-home --uid 1000 mcp
WORKDIR /app

COPY pyproject.toml ./
COPY src ./src
COPY data ./data
COPY config ./config
COPY README.md ./README.md

RUN pip install --no-cache-dir .

ENV MCP_CONNECT_HTTP_HOST=0.0.0.0 \
    MCP_CONNECT_HTTP_PORT=8080 \
    PYTHONUNBUFFERED=1

USER mcp
EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/healthz', timeout=2)" || exit 1

ENTRYPOINT ["mcp-connect-starter", "--transport", "http", "--host", "0.0.0.0", "--port", "8080"]
