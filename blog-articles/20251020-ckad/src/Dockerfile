FROM python:3.12-slim
WORKDIR /app

# Install uv
RUN python -m pip install --no-cache-dir uv

# Copy project definition and lock file
COPY pyproject.toml uv.lock ./
RUN python -m uv sync --no-dev

# Copy application
COPY app/ .

# Create non-root user
RUN useradd -m appuser
USER appuser

EXPOSE 5000

# Default environment (can be overridden)
ENV UVICORN_PORT=5000

# Start API inside uv virtual environment
CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "5000"]