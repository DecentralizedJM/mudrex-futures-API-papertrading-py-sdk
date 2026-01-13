# Mudrex Paper Trading API Server

FROM python:3.9-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install fastapi uvicorn

# Copy code
COPY . .

# Install SDK
RUN pip install -e .

# Run server
CMD ["python", "-m", "mudrex.api_server"]
