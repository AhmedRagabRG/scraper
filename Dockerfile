# Use official Playwright Python image (compatible with Python 3.13)
FROM mcr.microsoft.com/playwright/python:v1.57.0-jammy

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Copy requirements first (for better caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Install Playwright browsers (Chromium only for efficiency)
RUN playwright install chromium && \
    playwright install-deps chromium

# Copy application code
COPY scraper.py .
COPY main.py .
COPY api.py .
COPY reviews_scraper.py .

# Create output directory
RUN mkdir -p /app/output

# Expose port for API
EXPOSE 8000

# Default command: run API server
CMD ["python", "api.py"]
