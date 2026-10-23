"""Optional photo-to-ingredient detection with the YOLOv8n model that ships with the original project.

YOLOv8n is trained on COCO, which contains only a handful of foods. Results are suggestions for the user to
confirm. Images are decoded in memory (never written to disk with a client-supplied name).
"""
from __future__ import annotations

import io
import threading

from fastapi import APIRouter, File, HTTPException, UploadFile

from ..config import PROJECT_DIR

router = APIRouter(prefix="/api/vision", tags=["vision"])
MODEL_PATHS = [PROJECT_DIR / "models" / "vision" / "yolov8n.pt", PROJECT_DIR / "src" / "backend" / "yolov8n.pt"]
# COCO classes that are ingredients -> lexicon names. Prepared dishes (pizza, cake, ...) are not ingredients.
COCO_FOODS = {"banana": "banana", "apple": "apple", "orange": "orange", "broccoli": "broccoli", "carrot": "carrot"}
COCO_DISHES = {"sandwich", "hot dog", "pizza", "donut", "cake"}
MAX_BYTES = 8 * 1024 * 1024
_model = None
_lock = threading.Lock()


def _model_path():
    return next((p for p in MODEL_PATHS if p.exists()), None)


def _available() -> bool:
    if _model_path() is None:
        return False
    try:
        import ultralytics  # noqa: F401
    except ImportError:
        return False
    return True


def _get_model():
    global _model
    with _lock:
        if _model is None:
            from ultralytics import YOLO

            _model = YOLO(str(_model_path()))
        return _model


@router.get("/status")
def status():
    return {"available": _available(), "model": "yolov8n (COCO)" if _available() else None,
            "classes": sorted(COCO_FOODS),
            "note": "Photo detection uses a general object model that only recognises bananas, apples, oranges, "
                    "broccoli and carrots. Confirm or edit what it finds."}


@router.post("/detect")
async def detect(file: UploadFile = File(...)):
    if not _available():
        raise HTTPException(503, "Photo detection is not installed (pip install ultralytics)")
    data = await file.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise HTTPException(413, "Image too large (max 8 MB)")
    try:
        from PIL import Image

        img = Image.open(io.BytesIO(data))
        img.verify()
        img = Image.open(io.BytesIO(data)).convert("RGB")
    except Exception:
        raise HTTPException(415, "Unsupported or corrupt image")
    model = _get_model()
    results = model.predict(img, verbose=False, conf=0.35)
    found: dict[str, float] = {}
    dishes: set[str] = set()
    for r in results:
        for cls, conf in zip(r.boxes.cls.tolist(), r.boxes.conf.tolist()):
            label = model.names[int(cls)]
            if label in COCO_FOODS:
                found[label] = max(found.get(label, 0.0), float(conf))
            elif label in COCO_DISHES:
                dishes.add(label)
    return {"ingredients": [{"name": COCO_FOODS[k], "label": k, "confidence": round(v, 2)} for k, v in sorted(found.items(), key=lambda kv: -kv[1])],
            "dishes_seen": sorted(dishes)}
