# Mudrex Paper Trading API Server

FROM python:3.10-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy code
COPY . .

# Install SDK
RUN pip install -e .

# Run server
CMD ["python", "-m", "mudrex.api_server"]
