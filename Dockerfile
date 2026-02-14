# Use official Playwright Python image (compatible with Python 3.13)
FROM mcr.microsoft.com/playwright/python:v1.57.0-jammy

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DISPLAY=:99

# Install Xvfb and other dependencies for non-headless mode
RUN apt-get update && apt-get install -y \
    xvfb \
    xauth \
    x11-utils \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (for better caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Install Playwright browsers (Chromium only for efficiency)
RUN playwright install chromium && \
    playwright install-deps chromium

# Copy application code
COPY config.py .
COPY scraper.py .
COPY main.py .
COPY api.py .
COPY reviews_scraper.py .
COPY google_auth.py .

# Copy Google cookies if exists (optional)
COPY google_cookies.json* ./

# Create output directory
RUN mkdir -p /app/output

# Expose port for API
EXPOSE 8000

# Start Xvfb in background and run API server
CMD ["sh", "-c", "Xvfb :99 -screen 0 1920x1080x24 -ac +extension GLX +render -noreset & python api.py"]
