# Backend Dockerfile
FROM python:3.10-slim

WORKDIR /app

# Install system dependencies for OCR (PaddleOCR requirements)
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    iputils-ping \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Set PYTHONPATH
ENV PYTHONPATH=/app

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "server.routes.app:app", "--host", "0.0.0.0", "--port", "8000"]
