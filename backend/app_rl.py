import asyncio
import logging
import os
import cv2
import numpy as np
import base64
import time
import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from perception.fallback import FallbackDetector
from rl.orchestrator import AdaptiveTrafficOrchestrator
from rl.traffic_control import TrafficSignalController
from config import Config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("traffic-rl")

app = FastAPI(title="Adaptive Traffic RL Engine")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

frontend_dir = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.isdir(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

@app.get("/")
async def index():
    return FileResponse(os.path.join(frontend_dir, "index.html"))

# Initialize perception and RL
detector = FallbackDetector(Config)
detector.load()
orchestrator = AdaptiveTrafficOrchestrator(detector, Config)
signal_controller = TrafficSignalController()

# Storage for processed stats
processed_stats = []

@app.on_event("startup")
async def startup():
    logger.info("Adaptive Traffic RL Engine Started")

@app.post("/api/upload")
async def upload_video(file: UploadFile = File(...)):
    # Save file temporarily
    file_path = f"temp_{file.filename}"
    with open(file_path, "wb") as buffer:
        buffer.write(await file.read())
    
    return {"status": "uploaded", "filename": file.filename, "path": file_path}

@app.websocket("/ws/process")
async def process_video_ws(websocket: WebSocket):
    await websocket.accept()
    logger.info("Client connected for video processing")
    
    try:
        # For demo, we use a loop that simulates processing frames
        # or takes a path from the first message
        msg = await websocket.receive_text()
        data = json.loads(msg)
        video_path = data.get("path", None)
        
        cap = None
        if video_path and os.path.exists(video_path):
            cap = cv2.VideoCapture(video_path)
        else:
            logger.info("No video path provided, downloading external demo...")
            demo_url = "https://github.com/intel-iot-devkit/sample-videos/raw/master/car-detection.mp4"
            demo_path = "temp_demo_traffic.mp4"
            if not os.path.exists(demo_path):
                import urllib.request
                try:
                    logger.info("Downloading demo traffic video (this takes a few seconds)...")
                    req = urllib.request.Request(demo_url, headers={'User-Agent': 'Mozilla/5.0'})
                    with urllib.request.urlopen(req) as response, open(demo_path, 'wb') as out_file:
                        out_file.write(response.read())
                except Exception as e:
                    logger.error(f"Failed to download demo video: {e}")
            if os.path.exists(demo_path):
                cap = cv2.VideoCapture(demo_path)

        frame_idx = 0
        while True:
            t0 = time.time()
            
            if cap and cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    # Video ended, loop it
                    if frame_idx > 0:
                        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                        ret, frame = cap.read()
                    if not ret:
                        frame = np.zeros((480, 640, 3), dtype=np.uint8)
            else:
                ret = False
                frame = np.zeros((480, 640, 3), dtype=np.uint8)
                cv2.putText(frame, "Demo Download Failed.", (50, 50), 
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                time.sleep(0.03)
            # RL Orchestration
            results = orchestrator.process_frame(frame)
            
            # Draw detections
            for box in results["detections"].get("bounding_boxes", []):
                x1, y1, x2, y2 = map(int, box[:4])
                conf = float(box[4])
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.putText(frame, f"{conf:.2f}", (x1, max(10, y1-5)), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

            # Draw Tracker states
            for obj_id, centroid in orchestrator.tracker.objects.items():
                cx, cy = map(int, centroid)
                cv2.circle(frame, (cx, cy), 4, (0, 0, 255), -1)
                cv2.putText(frame, f"ID:{obj_id}", (cx-10, cy-10), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
            
            # Traffic Signal Logic
            density = results["detections"]["density_estimate"]
            # Mock density map for signals
            density_map = {
                "North": density,
                "South": max(0, density - 0.1),
                "East": min(1.0, density + 0.2),
                "West": max(0, density * 0.5)
            }
            signal_recs = signal_controller.recommend_timings(density_map)
            
            # Encode frame for FE
            _, buffer = cv2.imencode('.jpg', frame)
            frame_base64 = base64.b64encode(buffer).decode('utf-8')
            
            # Build payload
            payload = {
                "frame": frame_base64,
                "telemetry": {
                    "vehicle_count": results["detections"]["vehicle_count"],
                    "tracker_count": results["tracker_count"],
                    "avg_speed": results["avg_speed"],
                    "density": density,
                    "inference_time_ms": results["detections"]["inference_time_ms"],
                    "rl_action": results["rl_params"],
                    "rl_stats": results["rl_stats"],
                    "signal_control": signal_controller.get_status()
                },
                "processed_ms": (time.time() - t0) * 1000
            }
            
            await websocket.send_text(json.dumps(payload))
            frame_idx += 1
            
            # Frequency control based on RL action
            # (Note: detector already handles interval, but websocket needs to breathe)
            await asyncio.sleep(0.01)

    except WebSocketDisconnect:
        logger.info("Client disconnected")
    except Exception as e:
        logger.error(f"Error in processing: {e}")
    finally:
        if cap:
            cap.release()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
