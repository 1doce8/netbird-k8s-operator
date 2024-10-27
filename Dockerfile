FROM python:3.9-slim

WORKDIR /app

# Install required system packages
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc python3-dev && \
    rm -rf /var/lib/apt/lists/*

# Copy and install requirements first (for better caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy operator code
COPY operator.py .

# Set Python unbuffered environment
ENV PYTHONUNBUFFERED=1

# Run the operator
CMD ["kopf", "run", "--standalone", "--verbose", "operator.py"]
