# Base image (same as application for consistency)
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Copy requirements (shared with application)
# COPY requirements.txt requirements.txt

# Install dependencies
# RUN pip install -r requirements.txt

# Copy necessary files for worker (adjust paths as needed)
COPY users/tasks/*.py ./tasks 
# Add more COPY commands for task files from other directories if needed

# Specify startup command
CMD ["celery", "-A", "trayapp", "worker"]
