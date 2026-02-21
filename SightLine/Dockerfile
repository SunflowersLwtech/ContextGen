FROM python:3.12-slim

WORKDIR /app

# System deps for opencv-headless and onnxruntime
RUN apt-get update && \
    apt-get install -y --no-install-recommends libgl1 libglib2.0-0 && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source (excluding iOS, docs, dev, tests via .dockerignore)
COPY . .

EXPOSE 8080

CMD ["python", "-m", "uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8080"]
