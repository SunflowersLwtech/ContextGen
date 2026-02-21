# Face Recognition Solutions Research for SightLine

> **Research Date**: 2026-02-21
> **Source**: Parallel research agent - Face recognition APIs and libraries

---

## Executive Summary

**Bottom-line recommendation**: **InsightFace** (with the `buffalo_l` model pack) is the strongest choice. It offers 99.83% LFW accuracy, native ONNX CPU inference, 512-dim embeddings that fit Firestore's vector search (max 2048 dims), and clean Docker/Cloud Run compatibility. **DeepFace** is the strong runner-up.

---

## 1. Google Cloud Vision API -- Face Detection

### Verdict: NOT SUITABLE for face recognition / matching

- Does face **detection** (bounding boxes, landmarks), NOT recognition
- Expression/emotion detection (joy, sorrow, anger, surprise)
- Head pose estimation
- **Cannot generate face embeddings** for identity matching
- **No face collection/search API** (unlike Amazon Rekognition)
- Google has **no native face recognition cloud API at all**
- Pricing: at 1-2 FPS continuous = ~$3,900-$7,800/month (prohibitive)

---

## 2. face_recognition (ageitgey/face_recognition)

### Verdict: FUNCTIONAL but NOT RECOMMENDED -- unmaintained

- **Abandoned since ~2022**, 780 open issues, 53 unmerged PRs
- 128-dim embeddings (half modern systems)
- ~99.38% LFW accuracy (below modern ArcFace)
- Known racial bias issues
- dlib dependency: painful Docker builds (10-30 min compile), ~2GB image
- CPU speed: ~300-400ms/frame (HOG detector)

---

## 3. DeepFace (serengil/deepface)

### Verdict: STRONG OPTION -- excellent API, actively maintained

- 22.2k GitHub stars, actively maintained
- Supports ArcFace, FaceNet512, VGG-Face, GhostFaceNet, etc.
- ArcFace: 512-dim, 99.40% LFW, ~200ms CPU
- FaceNet512: 512-dim, 99.65% LFW, ~200ms CPU
- Simplest API: `DeepFace.represent()` is one line
- TensorFlow dependency adds ~1GB to Docker image

```python
from deepface import DeepFace

# Generate embedding
result = DeepFace.represent(
    img_path="photo.jpg",
    model_name="ArcFace",
    detector_backend="retinaface",
)
embedding = result[0]["embedding"]  # 512-dim
```

---

## 4. InsightFace (deepinsight/insightface) -- TOP RECOMMENDATION

### Why InsightFace

- **99.83% LFW accuracy** (state-of-the-art)
- 512-dim embeddings
- **ONNX Runtime** = fastest CPU inference (~100-250ms/frame)
- No TensorFlow/PyTorch dependency
- Docker image ~1.2GB (lightest option)
- Active development (Nov 2025)
- Built-in age, gender estimation

```python
import insightface
from insightface.app import FaceAnalysis
import numpy as np

app = FaceAnalysis(name="buffalo_l", providers=["CPUExecutionProvider"])
app.prepare(ctx_id=0, det_size=(640, 640))

# Register face
def register_face(image_path):
    img = cv2.imread(image_path)
    faces = app.get(img)
    if not faces:
        return None
    face = sorted(faces, key=lambda x: (x.bbox[2]-x.bbox[0])*(x.bbox[3]-x.bbox[1]), reverse=True)[0]
    emb = face.embedding / np.linalg.norm(face.embedding)
    return emb.tolist()

# Match face (cosine similarity > 0.4 = match)
def match_face(unknown_emb, known_persons, threshold=0.4):
    unknown = np.array(unknown_emb)
    unknown = unknown / np.linalg.norm(unknown)
    best_name, best_score = None, -1.0
    for person in known_persons:
        known = np.array(person["embedding"])
        score = float(np.dot(unknown, known))
        if score > threshold and score > best_score:
            best_score = score
            best_name = person["name"]
    return best_name, best_score
```

### Dockerfile

```dockerfile
FROM python:3.11-slim-bookworm
RUN apt-get update && apt-get install -y libgl1-mesa-glx libglib2.0-0
RUN pip install insightface==0.7.3 onnxruntime==1.17.0 opencv-python-headless numpy
RUN python -c "from insightface.app import FaceAnalysis; \
    app = FaceAnalysis(name='buffalo_l', providers=['CPUExecutionProvider']); \
    app.prepare(ctx_id=0)"
```

---

## 5. Google ML Kit -- Face Detection

- **Mobile-only** (Android/iOS) -- NO web/PWA support
- Detection only, NOT recognition
- For PWA pre-filtering: use MediaPipe Face Detection (TF.js, ~3MB) or BlazeFace

---

## 6. Cloud-based APIs

### Amazon Rekognition
- Full face recognition, but $2,600-5,200/month at 1-2 FPS
- Cross-cloud latency (AWS from GCP project)

### Azure Face API
- **Restricted access** -- requires formal Microsoft application
- Not practical for hackathon

### Google
- **No face recognition API exists** -- detection only via Cloud Vision

---

## 7. Firestore Integration

```python
from google.cloud.firestore_v1.vector import Vector
from google.cloud.firestore_v1.base_vector_query import DistanceMeasure

# Store
doc_ref.set({
    "name": "David",
    "embedding": Vector(embedding_512dim),
    "created_at": firestore.SERVER_TIMESTAMP,
})

# Search (native KNN)
results = collection.find_nearest(
    vector_field="embedding",
    query_vector=Vector(unknown_embedding),
    distance_measure=DistanceMeasure.DOT_PRODUCT,
    limit=1,
)
```

For < 100 people: load all embeddings at session start, do in-memory cosine similarity (faster than Firestore query per-frame).

---

## Comparative Summary

| Criterion | Cloud Vision | face_recognition | DeepFace | InsightFace | Rekognition |
|-----------|-------------|-----------------|----------|-------------|-------------|
| Recognition? | No | Yes | Yes | Yes | Yes |
| Embedding dims | N/A | 128 | 512 | **512** | Proprietary |
| LFW accuracy | N/A | 99.38% | 99.65% | **99.83%** | ~99.8% |
| CPU latency | N/A | 300-400ms | 150-500ms | **100-250ms** | 50-200ms (network) |
| Maintained? | Yes | **No** | Yes | **Yes** | Yes |
| Monthly cost @1FPS | $3,900 | Free | Free | **Free** | $2,600 |

---

## Sources

- [InsightFace GitHub](https://github.com/deepinsight/insightface)
- [DeepFace GitHub](https://github.com/serengil/deepface)
- [face_recognition GitHub](https://github.com/ageitgey/face_recognition)
- [Google Cloud Vision API](https://cloud.google.com/vision)
- [Firestore Vector Search](https://firebase.google.com/docs/firestore/vector-search)
- [Amazon Rekognition Pricing](https://aws.amazon.com/rekognition/pricing/)
- [Azure Face API Limited Access](https://learn.microsoft.com/en-us/azure/ai-foundry/responsible-ai/computer-vision/limited-access-identity)
- [InsightFace vs DeepFace](https://kitemetric.com/blogs/upgrading-face-recognition-from-deepface-to-insightface)
