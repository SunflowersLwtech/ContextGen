FROM python:3.12-slim

# System dependencies for InsightFace (OpenCV, ONNX Runtime)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1-mesa-glx libglib2.0-0 && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies first (cache layer)
COPY requirements-deploy.txt .
RUN pip install --no-cache-dir -r requirements-deploy.txt

# Download InsightFace buffalo_l models at build time
# (avoids downloading at runtime, which would slow cold starts)
RUN python -c "\
from insightface.app import FaceAnalysis; \
import os; \
app = FaceAnalysis(name='buffalo_l', \
    root=os.path.expanduser('~/.insightface'), \
    providers=['CPUExecutionProvider'], \
    allowed_modules=['detection', 'recognition']); \
app.prepare(ctx_id=0, det_size=(640, 640)); \
print('InsightFace buffalo_l models downloaded successfully')"

# Copy backend source (excluding iOS, docs, dev, tests via .dockerignore)
COPY . .

EXPOSE 8080

CMD ["python", "-m", "uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8080"]
