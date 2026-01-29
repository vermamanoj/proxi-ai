# Proxi Core - LLM orchestration, auth, sessions
# SECURITY: Runs as non-root user 'proxi'

FROM python:3.12-slim

WORKDIR /app

# Install system utilities
RUN apt-get update && apt-get install -y \
    gcc \
    procps \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN groupadd -r proxi && useradd -r -g proxi proxi

# Copy Linux-specific requirements (no Windows deps)
COPY requirements-linux.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r /app/requirements.txt

# Create data directory for SQLite
RUN mkdir -p /app/data

# Copy the application code into /app/backend to maintain import structure
COPY . /app/backend

# Set ownership to non-root user
RUN chown -R proxi:proxi /app

# Set PYTHONPATH so python can find the 'backend' module
ENV PYTHONPATH=/app

# Switch to non-root user
USER proxi

# Expose the port
EXPOSE 8000

# Start the server
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]