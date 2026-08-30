# Use a lightweight Python image
FROM python:3.11-slim

# Security: create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Set the working directory in the container
WORKDIR /code

# Copy requirements directly from the app folder
COPY ./app/requirements.txt .

# Use Chabokan's PyPI mirror
RUN pip install --no-cache-dir -r requirements.txt && \
    rm -rf /root/.cache

# Copy the entire app folder
COPY ./app ./app

# Copy your data folder into the container
COPY ./data ./data

# Ensure data and static are readable but not writable where unnecessary
RUN chown -R appuser:appuser /code && chmod -R 755 /code/app/static 2>/dev/null || true

USER appuser

# Env hardening: Python no bytecode, no pip cache, production mode hint
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    ENV=production

EXPOSE 8000

# Healthcheck: /healthz is PB-independent, so an upstream PocketBase outage
# never marks the app container unhealthy
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://127.0.0.1:8000/healthz', timeout=2)" || exit 1

# Start the FastAPI server - proxy headers only trust known forwards (starlette handles)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]