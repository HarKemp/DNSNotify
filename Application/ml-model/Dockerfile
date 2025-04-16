FROM python:3.10-slim

WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY main.py .
COPY dns_classifier.joblib .

# Create logs directory
RUN mkdir -p /logs && chmod 777 /logs

EXPOSE 5000

# Run the Flask application
CMD ["python", "-u", "main.py"]