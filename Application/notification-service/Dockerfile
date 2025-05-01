# Use the same Python base image for consistency
FROM python:3.11-slim

WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY notification.py .

# Run the notification service application
CMD ["python", "-u", "notification.py"]
