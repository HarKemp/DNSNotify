FROM python:3.11-slim

WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY main.py .
COPY ml_processing.py .
COPY dns_classifier.joblib .

# Run the Flask application
CMD ["python", "-u", "main.py"]