"""
System Configuration for Hybrid Predictive Traffic Intelligence System v2
Enhanced with: anomaly detection, cross-modal validation, CCTV simulation,
extended prediction, smart alerts, and cause classification.
"""
import os

class Config:
    # ── GPU / Device ───────────────────────────────────────────────────
    GPU_AVAILABLE = False
    DEVICE = "cpu"
    MODE = "LITE"

    # ── Perception Layer ───────────────────────────────────────────────
    YOLO_MODEL = "yolov8n.pt"
    GPU_FRAME_INTERVAL = 1
    CPU_FRAME_INTERVAL = 5
    DETECTION_CONFIDENCE = 0.35
    VEHICLE_CLASSES = [2, 3, 5, 7]  # car, motorcycle, bus, truck

    # Dynamic resolution scaling
    GPU_RESOLUTION = (640, 480)
    CPU_RESOLUTION = (320, 240)

    # Anomaly detection in perception
    STOPPED_VEHICLE_IOU_THRESHOLD = 0.85   # IoU between frames for "stopped"
    CLUSTERING_DENSITY_THRESHOLD = 0.8     # Sudden clustering alert
    ANOMALY_FRAME_HISTORY = 5              # Frames to track for anomaly

    # ── CCTV Simulation ────────────────────────────────────────────────
    CCTV_FRAME_WIDTH = 640
    CCTV_FRAME_HEIGHT = 400
    CCTV_FPS_SIM = 8            # Simulated FPS for CCTV canvas
    CCTV_SAMPLE_RATE = 3        # Process 1 frame every N seconds

    # ── Data Fusion ────────────────────────────────────────────────────
    CONGESTION_W1 = 0.45  # Weight for density
    CONGESTION_W2 = 0.55  # Weight for speed inverse
    MAX_SPEED_KPH = 60
    MAX_DENSITY = 50

    # Cross-modal validation thresholds
    CROSSMODAL_DISAGREE_THRESHOLD = 0.35  # CI diff to flag disagreement
    FALSE_POSITIVE_LABEL = "⚠️ API-only (visual clear)"
    EARLY_WARNING_LABEL = "🔔 Visual-only (early warning)"

    # ── Prediction ─────────────────────────────────────────────────────
    EMA_ALPHA = 0.3
    PREDICTION_HORIZON = 9      # 9 × 5 min = 45 min
    TREND_WINDOW = 12
    PREDICTION_STEP_MINUTES = 5

    # Optional LSTM
    LSTM_ENABLED = False         # Set True if ONNX model available
    LSTM_MODEL_PATH = "models/lstm_traffic.onnx"
    LSTM_INPUT_STEPS = 12
    LSTM_HIDDEN_SIZE = 32

    # ── Propagation ────────────────────────────────────────────────────
    PROPAGATION_DECAY = 0.6
    PROPAGATION_THRESHOLD = 0.4
    MAX_PROPAGATION_HOPS = 3

    # ── Incident & Anomaly Detection ───────────────────────────────────
    DENSITY_SPIKE_THRESHOLD = 0.7
    SPEED_DROP_THRESHOLD = 0.3
    INCIDENT_CONFIDENCE_MIN = 0.6

    # ── Smart Alerts ───────────────────────────────────────────────────
    ALERT_PREDICTION_THRESHOLD = 0.65   # Predicted CI to trigger alert
    ALERT_LOOKAHEAD_STEPS = 4           # Steps ahead to scan (20 min)
    MAX_ACTIVE_ALERTS = 10

    # ── Cause Classification ───────────────────────────────────────────
    CAUSE_HIGH_DENSITY_THRESHOLD = 0.6
    CAUSE_SUDDEN_STOP_SPEED_DROP = 0.35
    CAUSE_PROPAGATION_ADDITION = 0.1

    # ── Pipeline ───────────────────────────────────────────────────────
    PIPELINE_INTERVAL_SEC = 5
    CACHE_TTL_SEC = 30
    HISTORY_BUFFER_SIZE = 60    # Keep last 60 data points

    # ── Demo Mode ──────────────────────────────────────────────────────
    DEMO_MODE = True
    DEMO_CITY = "Mumbai"

    # ── Server ─────────────────────────────────────────────────────────
    HOST = "0.0.0.0"
    PORT = 8000
    WS_PATH = "/ws/traffic"

    @classmethod
    def summary(cls):
        return {
            "device": cls.DEVICE,
            "mode": cls.MODE,
            "gpu_available": cls.GPU_AVAILABLE,
            "demo_mode": cls.DEMO_MODE,
            "yolo_model": cls.YOLO_MODEL,
            "prediction_horizon_min": cls.PREDICTION_HORIZON * cls.PREDICTION_STEP_MINUTES,
            "lstm_enabled": cls.LSTM_ENABLED,
            "crossmodal_validation": True,
            "anomaly_detection": True,
            "smart_alerts": True,
        }
