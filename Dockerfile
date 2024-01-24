# Base image for building dependencies (multi-stage build)
FROM python:3.12-slim as builder

# Set working directory
WORKDIR /app

# Copy requirements
COPY requirements.txt requirements.txt

RUN apt-get update && apt-get install -y gcc

# Upgrade pip
RUN pip install --upgrade pip

RUN pip install gunicorn psycopg2-binary whitenoise

# Install dependencies with increased timeout
RUN pip install --default-timeout=100 --no-cache-dir -r requirements.txt

# Base image for the final application
FROM python:3.12-slim as final

# Set working directory
WORKDIR /app

# Copy project files
COPY . .

# Copy dependencies from builder stage
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages

EXPOSE 8000

# Startup command for the application
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

# Startup command for celery
# CMD ["celery", "-A", "config", "worker", "-l", "info"]2
