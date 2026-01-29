# Proxi Core - LLM orchestration, auth, sessions
# SECURITY: Runs as non-root user 'proxi' via entrypoint

FROM python:3.12-slim

WORKDIR /app

# Install system utilities + gosu for proper user switching
RUN apt-get update && apt-get install -y \
    gcc \
    procps \
    curl \
    gosu \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN groupadd -r proxi && useradd -r -g proxi proxi

# Copy Linux-specific requirements (no Windows deps)
COPY requirements-linux.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r /app/requirements.txt

# Create data directory for SQLite
RUN mkdir -p /app/data && chown proxi:proxi /app/data

# Copy the application code into /app/backend to maintain import structure
COPY . /app/backend

# Copy and setup entrypoint script
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Set ownership to non-root user
RUN chown -R proxi:proxi /app

# Set PYTHONPATH so python can find the 'backend' module
ENV PYTHONPATH=/app

# Expose the port
EXPOSE 8000

# Use entrypoint to fix permissions on mounted volumes before starting
# Runs as root initially, switches to proxi user via gosu
ENTRYPOINT ["/app/entrypoint.sh"]