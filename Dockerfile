FROM python:3.9-slim AS backend

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install additional packages for WebSockets, Channels, and health checks
RUN pip install --no-cache-dir requests daphne channels-redis anthropic whitenoise

# Copy backend code
COPY backend/ /app/backend/

# Final stage
FROM python:3.9-slim

WORKDIR /app

# Copy Python dependencies from backend stage
COPY --from=backend /usr/local/lib/python3.9/site-packages/ /usr/local/lib/python3.9/site-packages/
COPY --from=backend /usr/local/bin/ /usr/local/bin/

# Copy backend code
COPY backend/ /app/backend/

# Set working directory to backend
WORKDIR /app/backend

# Run the application
CMD ["daphne", "takeoff_tool.asgi:application", "--port", "8000", "--bind", "0.0.0.0"]
