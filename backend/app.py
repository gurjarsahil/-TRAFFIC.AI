"""
FastAPI Server v2 — Enhanced with CCTV endpoints, smart alerts, and modular services.
"""
import asyncio
import logging
import os
import sys

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

sys.path.insert(0, os.path.dirname(__file__))

from config import Config
from pipeline import TrafficPipeline

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
)
logger = logging.getLogger("traffic-server")

app = FastAPI(
    title="Hybrid Predictive Traffic Intelligence System v2",
    description="GPU-accelerated traffic analysis with CCTV preview, cross-modal validation, cause classification, and smart alerts",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

frontend_dir = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.isdir(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

pipeline = TrafficPipeline()


@app.on_event("startup")
async def startup():
    logger.info("=" * 65)
    logger.info("  HYBRID PREDICTIVE TRAFFIC INTELLIGENCE SYSTEM v2")
    logger.info(f"  Mode: {Config.MODE} | Device: {Config.DEVICE}")
    logger.info(f"  GPU: {Config.GPU_AVAILABLE} | Demo: {Config.DEMO_MODE}")
    logger.info(f"  Prediction: {Config.PREDICTION_HORIZON * Config.PREDICTION_STEP_MINUTES}min horizon")
    logger.info(f"  Features: Cross-Modal ✓ | Cause-Classification ✓ | Smart Alerts ✓")
    logger.info("=" * 65)
    asyncio.create_task(pipeline.start())


@app.on_event("shutdown")
async def shutdown():
    await pipeline.stop()


@app.get("/")
async def root():
    index_path = os.path.join(frontend_dir, "index_hybrid.html")
    if os.path.isfile(index_path):
        return FileResponse(index_path)
    return {"message": "Traffic Intelligence System v2 API", "docs": "/docs"}


@app.get("/api/status")
async def system_status():
    return {
        "status": "running",
        "config": Config.summary(),
        "pipeline_tick": pipeline._tick,
    }


@app.get("/api/network")
async def get_network():
    return pipeline.road_network.to_serializable()


@app.get("/api/snapshot")
async def get_snapshot():
    result = pipeline.get_last_result()
    if result:
        return result
    return {"message": "Pipeline initializing..."}


@app.get("/api/node/{node_id}")
async def get_node_detail(node_id: str):
    try:
        node = pipeline.road_network.get_node(node_id)
        result = pipeline.get_last_result()
        explanation = result["explanations"].get(node_id, {}) if result else {}
        prediction = result["predictions"].get(node_id, []) if result else []
        return {
            "node": {
                "id": node_id,
                **{k: v for k, v in node.items() if k != "history"},
                "history": node.get("history", [])[-30:],
            },
            "explanation": explanation,
            "prediction": prediction,
        }
    except KeyError:
        return JSONResponse(status_code=404, content={"error": "Node not found"})


@app.get("/api/alerts")
async def get_alerts():
    return {
        "incidents": pipeline.incident_detector.get_active_incidents(),
        "smart_alerts": pipeline.smart_alerts.get_active_alerts(),
    }


@app.get("/api/cctv/frame")
async def get_cctv_frame(node_id: str = Query(None)):
    """Get current CCTV frame data for canvas rendering."""
    if node_id:
        pipeline.set_cctv_node(node_id)
    result = pipeline.get_last_result()
    if result and result.get("cctv_frame"):
        return result["cctv_frame"]
    return {"message": "No CCTV data available"}


@app.post("/api/cctv/switch")
async def switch_cctv(node_id: str = Query(...)):
    return pipeline.set_cctv_node(node_id)


@app.post("/api/simulate/blockage")
async def simulate_blockage(node_id: str = Query(...), duration: int = Query(10)):
    return pipeline.simulate_blockage(node_id, duration)


@app.post("/api/mode")
async def set_mode(mode: str = Query(...)):
    return pipeline.set_mode(mode.upper())


@app.get("/api/incidents")
async def get_incidents():
    return {"incidents": pipeline.incident_detector.get_active_incidents()}


# ── WebSocket ──────────────────────────────────────────────────
@app.websocket("/ws/traffic")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    pipeline.subscribe(websocket)
    logger.info("WS client connected")
    try:
        while True:
            data = await websocket.receive_text()
            try:
                import json
                cmd = json.loads(data)
                action = cmd.get("action")
                resp = None
                if action == "simulate_blockage":
                    resp = pipeline.simulate_blockage(
                        cmd.get("node_id", "N10"), cmd.get("duration", 10)
                    )
                elif action == "set_mode":
                    resp = pipeline.set_mode(cmd.get("mode", "LITE"))
                elif action == "switch_cctv":
                    resp = pipeline.set_cctv_node(cmd.get("node_id", "N10"))

                if resp:
                    await websocket.send_text(json.dumps({
                        "type": "command_response", "result": resp
                    }))
            except Exception:
                pass
    except WebSocketDisconnect:
        pipeline.unsubscribe(websocket)
        logger.info("WS client disconnected")


for pkg in ["perception", "ingestion", "fusion", "prediction",
            "propagation", "explainability", "alerts", "demo"]:
    init_path = os.path.join(os.path.dirname(__file__), pkg, "__init__.py")
    os.makedirs(os.path.dirname(init_path), exist_ok=True)
    if not os.path.exists(init_path):
        open(init_path, "w").close()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host=Config.HOST, port=Config.PORT, reload=False, log_level="info")
