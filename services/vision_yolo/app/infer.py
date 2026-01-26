"""
AFASA 2.0 - YOLO Inference Engine
"""
from typing import List, Dict, Any
from pathlib import Path
import io
from PIL import Image
import numpy as np


class YOLOInference:
    def __init__(self, model_path: str = "yolov8n.pt"):
        self._model = None
        self._model_path = model_path
        self._load_model()
    
    def _load_model(self):
        """Load YOLO model"""
        try:
            from ultralytics import YOLO
            self._model = YOLO(self._model_path)
        except Exception as e:
            print(f"Failed to load YOLO model: {e}")
            self._model = None
    
    def infer(
        self,
        image_data: bytes,
        threshold: float = 0.5,
        classes: List[str] = None
    ) -> Dict[str, Any]:
        """
        Run inference on image.
        Returns detections list and annotated image.
        """
        if self._model is None:
            return {"detections": [], "annotated_data": None}
        
        # Load image
        img = Image.open(io.BytesIO(image_data))
        
        # Run inference
        results = self._model(img, conf=threshold)
        
        detections = []
        for result in results:
            boxes = result.boxes
            for box in boxes:
                x1, y1, x2, y2 = box.xyxyn[0].tolist()  # Normalized coords
                conf = float(box.conf[0])
                cls_id = int(box.cls[0])
                label = result.names[cls_id]
                
                # Filter by classes if specified
                if classes and label not in classes:
                    continue
                
                detections.append({
                    "label": label,
                    "confidence": round(conf, 3),
                    "bbox": [round(x1, 4), round(y1, 4), round(x2, 4), round(y2, 4)]
                })
        
        # Generate annotated image
        annotated = results[0].plot()
        annotated_img = Image.fromarray(annotated)
        
        buffer = io.BytesIO()
        annotated_img.save(buffer, format="JPEG", quality=85)
        annotated_data = buffer.getvalue()
        
        return {
            "detections": detections,
            "annotated_data": annotated_data
        }


# Plant disease detection model (custom trained)
class PlantDiseaseDetector(YOLOInference):
    """
    Custom YOLO model for plant disease detection.
    Expected labels: leaf_blight, powdery_mildew, rust, healthy, etc.
    """
    
    DISEASE_LABELS = [
        "leaf_blight",
        "powdery_mildew",
        "rust",
        "bacterial_spot",
        "mosaic_virus",
        "anthracnose",
        "healthy"
    ]
    
    def __init__(self, model_path: str = "plant_disease.pt"):
        # Fall back to base YOLO if custom model not found
        if not Path(model_path).exists():
            model_path = "yolov8n.pt"
        super().__init__(model_path)


_detector: YOLOInference = None


def get_detector() -> YOLOInference:
    global _detector
    if _detector is None:
        _detector = PlantDiseaseDetector()
    return _detector
