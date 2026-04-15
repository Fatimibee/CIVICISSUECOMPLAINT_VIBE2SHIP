# 1. Use a lightweight Python image
FROM python:3.10-slim

# 2. Set working directory
WORKDIR /app

# 3. Install system dependencies (needed for PIL, OpenCV, torch etc.)
RUN apt-get update && apt-get install -y \
    build-essential \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# 4. Copy requirements first (for caching)
COPY requirements.txt .

# 5. Install Python dependencies
RUN pip install --no-cache-dir --default-timeout=100 -r requirements.txt

# 6. Copy project files
COPY . .

# 7. Fix Python path for module imports (VERY IMPORTANT for your structure)
ENV PYTHONPATH=/app

# ❌ REMOVE THIS (not needed in HF, can cause confusion)
# EXPOSE 8000

# 8. Run FastAPI (HF requires port 7860)
CMD ["uvicorn", "App.app:app", "--host", "0.0.0.0", "--port", "7860"]