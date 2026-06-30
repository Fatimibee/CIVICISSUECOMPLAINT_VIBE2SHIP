# 1. Use a lightweight official Python image
FROM python:3.10-slim

# 2. Set working directory
WORKDIR /app

# 3. Install system dependencies required for ML & image utilities
RUN apt-get update && apt-get install -y \
    build-essential \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# 4. Copy requirements first for Docker caching optimization
COPY requirements.txt .

# 5. Install dependencies
RUN pip install --no-cache-dir --default-timeout=100 -r requirements.txt

# 6. Copy all project source directories and files
COPY . .

# 7. Set Python path so App, Agent, and Core folders resolve imports properly
ENV PYTHONPATH=/app

# 8. Run the FastAPI application using the dynamically assigned Google Cloud port
CMD ["sh", "-c", "uvicorn App.app:app --host 0.0.0.0 --port ${PORT:-8080}"]