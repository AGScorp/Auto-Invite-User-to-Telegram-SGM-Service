# Use official Python 3.12 slim image
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TZ=Asia/Bangkok

# Install system dependencies
RUN apt-get update && apt-get install -y \
    # Basic tools
    gcc \
    g++ \
    git \
    curl \
    # Required for Pyrogram
    libssl-dev \
    libffi-dev \
    # Timezone
    tzdata \
    # Clean up
    && rm -rf /var/lib/apt/lists/* \
    && ln -sf /usr/share/zoneinfo/$TZ /etc/localtime \
    && echo $TZ > /etc/timezone

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create directory for session files if needed
RUN mkdir -p /app/sessions

# Expose the port the app runs on
EXPOSE 8200

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8200/ || exit 1

# Run the application
CMD ["python", "main.py"]