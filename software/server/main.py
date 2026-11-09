"""
Marshall (Bittle X Add-on) Main Bridge Server.

Responsibilities:
1. Accept a live camera video stream + MLX90614 thermal readings over WiFi:
   - Push mode: WebSocket `/ws/camera` or HTTP `POST /api/camera/frame`
   - Pull mode: Pulls MJPEG stream from `CAMERA_STREAM_URL` (or `http://<CAMERA_IP>:8081/stream`)
2. Serve the Web + WebXR (VR) application at `/`
3. Broadcast the video stream to browsers & VR headsets via:
   - `GET /stream` (multipart MJPEG stream per `docs/interfaces.md`)
   - `GET /frame.jpg` (low-latency single JPEG for WebGL textures)
   - `WS /ws` (JSON telemetry & control per `docs/interfaces.md`, plus optional binary frame push for VR)
"""

import argparse
import asyncio
import contextlib
import json
import os
import time
from contextlib import asynccontextmanager
from pathlib import Path

import cv2
import httpx
import numpy as np
import uvicorn
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import (
    FileResponse,
    HTMLResponse,
    JSONResponse,
    Response,
    StreamingResponse,
)
from fastapi.staticfiles import StaticFiles

STATIC_DIR = Path(__file__).parent / "static"


class StreamState:
    def __init__(self) -> None:
        self.latest_jpeg: bytes = self._make_placeholder_frame("Waiting for WiFi camera stream...")
        self.last_frame_time: float = 0.0
        self.frame_seq: int = 0
        self.fps: float = 0.0
        self._fps_counter: int = 0
        self._fps_window_start: float = time.monotonic()
        self.frame_event = asyncio.Event()

        # Thermal sensor state (MLX90614)
        self.temperature: float = 22.5
        self.ambient: float = 22.5
        self.fire_level: int = 0
        self.fire_detected: bool = False
        # A real MLX90614 (POST /api/sensor) always wins over the camera simulator's fake readings
        self.last_live_sensor_time: float = 0.0
        self.last_sim_sensor_time: float = 0.0

        # Robot status (simulated until BiBoard WebSocket is connected)
        self.battery_voltage: float = 7.6
        self.water_percent: int = 100
        self.biboard_connected: bool = False
        self.last_drive = {"x": 0.0, "y": 0.0}
        self.extinguish_task: asyncio.Task | None = None

        # Connected browser / VR clients on /ws
        self.clients: set[WebSocket] = set()
        # Subset of clients that requested binary JPEG frames over /ws (for low-latency WebXR)
        self.vr_frame_clients: set[WebSocket] = set()

    @property
    def camera_connected(self) -> bool:
        return (time.monotonic() - self.last_frame_time) < 3.0

    def update_frame(self, jpeg_bytes: bytes) -> None:
        if not jpeg_bytes:
            return
        now = time.monotonic()
        self.latest_jpeg = jpeg_bytes
        self.last_frame_time = now
        self.frame_seq += 1
        self._fps_counter += 1
        elapsed = now - self._fps_window_start
        if elapsed >= 1.0:
            self.fps = round(self._fps_counter / elapsed, 1)
            self._fps_counter = 0
            self._fps_window_start = now
        self.frame_event.set()
        self.frame_event = asyncio.Event()

    @property
    def sensor_source(self) -> str:
        """'sensor' = real MLX90614, 'sim' = camera simulator, 'none' = no readings yet."""
        now = time.monotonic()
        if now - self.last_live_sensor_time < 3.0:
            return "sensor"
        if now - self.last_sim_sensor_time < 3.0:
            return "sim"
        return "none"

    def update_thermal(self, temperature: float, ambient: float, live: bool = False) -> None:
        now = time.monotonic()
        if live:
            self.last_live_sensor_time = now
        else:
            self.last_sim_sensor_time = now
            if now - self.last_live_sensor_time < 3.0:
                return  # real sensor is active: ignore simulated values
        self.temperature = round(float(temperature), 2)
        self.ambient = round(float(ambient), 2)
        # Compute fire meter level (0-100) from (temperature - ambient) per docs/interfaces.md
        delta = max(0.0, self.temperature - self.ambient)
        # Full scale (~100) at +35C above ambient (tea-light candle at close range)
        self.fire_level = int(min(100, round((delta / 35.0) * 100)))
        self.fire_detected = self.fire_level >= 45

    @staticmethod
    def _make_placeholder_frame(message: str) -> bytes:
        img = np.zeros((480, 640, 3), dtype=np.uint8)
        img[:] = (28, 24, 22)
        cv2.putText(
            img,
            "MARSHALL SERVER - CAMERA OFFLINE",
            (95, 210),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.75,
            (90, 180, 255),
            2,
            cv2.LINE_AA,
        )
        cv2.putText(
            img,
            message,
            (115, 255),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (200, 200, 200),
            1,
            cv2.LINE_AA,
        )
        ok, buf = cv2.imencode(".jpg", img, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
        return buf.tobytes() if ok else b""


state = StreamState()


async def broadcast_json(payload: dict) -> None:
    if not state.clients:
        return
    data = json.dumps(payload)
    stale: list[WebSocket] = []
    for ws in list(state.clients):
        try:
            await ws.send_text(data)
        except (WebSocketDisconnect, RuntimeError, ConnectionResetError, OSError):
            stale.append(ws)
    for ws in stale:
        state.clients.discard(ws)
        state.vr_frame_clients.discard(ws)


async def broadcast_binary_frame(jpeg_bytes: bytes) -> None:
    if not state.vr_frame_clients:
        return
    stale: list[WebSocket] = []
    for ws in list(state.vr_frame_clients):
        try:
            await ws.send_bytes(jpeg_bytes)
        except (WebSocketDisconnect, RuntimeError, ConnectionResetError, OSError):
            stale.append(ws)
    for ws in stale:
        state.vr_frame_clients.discard(ws)


async def telemetry_loop() -> None:
    """Broadcast `status` (1 Hz) and `fire` (4 Hz) messages per `docs/interfaces.md`."""
    tick = 0
    while True:
        await asyncio.sleep(0.25)
        tick += 1

        # Fire message (4 times per second, docs/interfaces.md requires >= 2 Hz)
        await broadcast_json(
            {
                "type": "fire",
                "detected": state.fire_detected,
                "level": state.fire_level,
                "temperature": state.temperature,
                "ambient": state.ambient,
                "source": state.sensor_source,
            }
        )

        # Status message (every 1 second)
        if tick % 4 == 0:
            await broadcast_json(
                {
                    "type": "status",
                    "battery": state.battery_voltage,
                    "water": state.water_percent,
                    "fps": state.fps if state.camera_connected else 0.0,
                    "connected": {
                        "biboard": state.biboard_connected,
                        "camera": state.camera_connected,
                    },
                }
            )


async def camera_pull_loop(stream_url: str, sensor_url: str | None) -> None:
    """
    Optional PULL mode: pull multipart MJPEG stream from an ESP32/simulator HTTP endpoint
    if no camera is actively pushing to `/ws/camera`.
    """
    print(f"[SERVER] Camera PULL loop configured for {stream_url}")
    async with httpx.AsyncClient(timeout=5.0) as client:
        while True:
            # Skip pulling if a camera is already pushing frames via WebSocket/HTTP
            if state.camera_connected:
                await asyncio.sleep(1.0)
                continue

            try:
                async with client.stream("GET", stream_url) as resp:
                    buffer = b""
                    async for chunk in resp.aiter_bytes(chunk_size=4096):
                        buffer += chunk
                        start = buffer.find(b"\xff\xd8")
                        end = buffer.find(b"\xff\xd9")
                        if start != -1 and end != -1 and end > start:
                            jpeg = buffer[start : end + 2]
                            buffer = buffer[end + 2 :]
                            state.update_frame(jpeg)
                            await broadcast_binary_frame(jpeg)

                        if sensor_url and state.frame_seq % 10 == 0:
                            try:
                                sresp = await client.get(sensor_url, timeout=1.0)
                                if sresp.status_code == 200:
                                    sdata = sresp.json()
                                    state.update_thermal(
                                        sdata.get("temperature", 22.5),
                                        sdata.get("ambient", 22.5),
                                    )
                            except (httpx.HTTPError, ValueError):
                                pass
            except asyncio.CancelledError:
                break
            except (httpx.HTTPError, OSError):
                await asyncio.sleep(2.0)


async def simulate_extinguish_routine() -> None:
    """Simulate the extinguish state machine from `docs/interfaces.md`."""
    try:
        for step, duration in [("searching", 1.5), ("positioning", 1.8), ("spraying", 2.0)]:
            await broadcast_json({"type": "extinguish_state", "state": step})
            await asyncio.sleep(duration)
        state.water_percent = max(0, state.water_percent - 15)
        await broadcast_json({"type": "extinguish_state", "state": "done"})
        await broadcast_json({"type": "fire_out"})
    except asyncio.CancelledError:
        await broadcast_json({"type": "extinguish_state", "state": "failed"})


_lifespan_refs = 0
_background_tasks: list[asyncio.Task] = []


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # With --https-port two listeners share this app (and its state): start background tasks once.
    global _lifespan_refs
    _lifespan_refs += 1
    if _lifespan_refs == 1:
        _background_tasks.append(asyncio.create_task(telemetry_loop()))
        _start_camera_pull()
    try:
        yield
    finally:
        _lifespan_refs -= 1
        if _lifespan_refs == 0:
            for task in _background_tasks:
                task.cancel()
            _background_tasks.clear()


def _start_camera_pull() -> None:

    camera_ip = os.getenv("CAMERA_IP", "").strip()
    stream_url = os.getenv("CAMERA_STREAM_URL", "").strip()
    sensor_url = os.getenv("CAMERA_SENSOR_URL", "").strip()
    if not stream_url and camera_ip:
        stream_url = f"http://{camera_ip}:8081/stream"
        sensor_url = f"http://{camera_ip}:8081/sensor"

    if stream_url:
        _background_tasks.append(asyncio.create_task(camera_pull_loop(stream_url, sensor_url or None)))


app = FastAPI(title="Marshall Bittle X Server", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", response_class=HTMLResponse)
async def serve_index():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/stream")
async def mjpeg_stream():
    """
    Serve the multipart MJPEG video stream to browsers (`https://<laptop-ip>/stream`
    as specified in `docs/interfaces.md`).
    """

    async def generate():
        last_sent_seq = -1
        while True:
            if state.frame_seq == last_sent_seq:
                try:
                    await asyncio.wait_for(state.frame_event.wait(), timeout=0.5)
                except TimeoutError:
                    pass
            last_sent_seq = state.frame_seq
            jpeg = state.latest_jpeg
            header = (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n"
                b"Content-Length: " + str(len(jpeg)).encode() + b"\r\n\r\n"
            )
            yield header + jpeg + b"\r\n"

    return StreamingResponse(
        generate(),
        media_type="multipart/x-mixed-replace; boundary=frame",
        headers={"Cache-Control": "no-store, no-cache, must-revalidate, max-age=0"},
    )


@app.get("/frame.jpg")
async def single_frame():
    """Return the latest JPEG frame (used by Three.js / WebXR fallback loader)."""
    return Response(
        content=state.latest_jpeg,
        media_type="image/jpeg",
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Access-Control-Allow-Origin": "*",
        },
    )


@app.post("/api/camera/frame")
async def post_camera_frame(request: Request):
    """HTTP PUSH endpoint: allows a WiFi camera to POST raw JPEG frames directly."""
    body = await request.body()
    if body:
        state.update_frame(body)
        await broadcast_binary_frame(body)
        return JSONResponse({"ok": True, "seq": state.frame_seq})
    return JSONResponse({"ok": False}, status_code=400)


@app.post("/api/sensor")
async def post_sensor(request: Request):
    """
    Real heat sensor ingest: the BiBoard (MLX90614 over I2C) POSTs
    {"temperature": <object degC>, "ambient": <ambient degC>} over WiFi.
    """
    try:
        data = await request.json()
        temperature = float(data["temperature"])
        ambient = float(data["ambient"])
    except (ValueError, KeyError, TypeError):
        return JSONResponse({"ok": False, "error": "need numeric temperature and ambient"}, status_code=400)
    # MLX90614 range is -70..380 degC for the object, -40..125 degC for the ambient/die
    if not (-70.0 <= temperature <= 380.0 and -40.0 <= ambient <= 125.0):
        return JSONResponse({"ok": False, "error": "reading out of sensor range"}, status_code=400)
    state.update_thermal(temperature, ambient, live=True)
    return JSONResponse({"ok": True, "level": state.fire_level})


@app.websocket("/ws/camera")
async def ws_camera_ingest(ws: WebSocket):
    """
    WebSocket PUSH endpoint: accepts binary JPEG frames and JSON thermal sensor readings
    from the XIAO ESP32-S3 camera or the camera simulator over WiFi.
    """
    await ws.accept()
    print(f"[SERVER] Camera stream connected from {ws.client}")
    try:
        while True:
            msg = await ws.receive()
            if msg.get("type") == "websocket.disconnect":
                break
            if msg.get("bytes"):
                jpeg = msg["bytes"]
                state.update_frame(jpeg)
                await broadcast_binary_frame(jpeg)
            elif msg.get("text"):
                try:
                    data = json.loads(msg["text"])
                    if data.get("type") == "sensor":
                        state.update_thermal(
                            data.get("temperature", 22.5),
                            data.get("ambient", 22.5),
                        )
                except json.JSONDecodeError:
                    pass
    except WebSocketDisconnect:
        pass
    except (RuntimeError, ConnectionResetError, OSError) as exc:
        print(f"[SERVER] Camera stream error: {exc}")
    finally:
        print("[SERVER] Camera stream disconnected")


@app.websocket("/ws")
async def ws_client(ws: WebSocket):
    """
    Browser & Quest 2 WebXR WebSocket endpoint (`/ws` per `docs/interfaces.md`).
    Handles JSON commands (`drive`, `extinguish`, `stop`) and broadcasts `status`, `fire`,
    `extinguish_state`, and `fire_out` messages.
    Also supports `{"type": "subscribe_frames", "enabled": true}` to stream binary JPEG
    frames over the same WebSocket for high-FPS WebXR texture rendering.
    """
    await ws.accept()
    state.clients.add(ws)
    try:
        # Send immediate initial status
        await ws.send_text(
            json.dumps(
                {
                    "type": "status",
                    "battery": state.battery_voltage,
                    "water": state.water_percent,
                    "fps": state.fps if state.camera_connected else 0.0,
                    "connected": {
                        "biboard": state.biboard_connected,
                        "camera": state.camera_connected,
                    },
                }
            )
        )
        while True:
            raw = await ws.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                continue

            msg_type = msg.get("type")
            if msg_type == "drive":
                state.last_drive = {
                    "x": float(msg.get("x", 0.0)),
                    "y": float(msg.get("y", 0.0)),
                }
            elif msg_type == "extinguish":
                if state.extinguish_task is None or state.extinguish_task.done():
                    state.extinguish_task = asyncio.create_task(simulate_extinguish_routine())
            elif msg_type == "stop":
                state.last_drive = {"x": 0.0, "y": 0.0}
                if state.extinguish_task and not state.extinguish_task.done():
                    state.extinguish_task.cancel()
            elif msg_type == "subscribe_frames":
                if msg.get("enabled", True):
                    state.vr_frame_clients.add(ws)
                else:
                    state.vr_frame_clients.discard(ws)
    except WebSocketDisconnect:
        pass
    finally:
        state.clients.discard(ws)
        state.vr_frame_clients.discard(ws)


if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


async def serve_http_and_https(http_config: uvicorn.Config, https_config: uvicorn.Config) -> None:
    """Run an HTTP and an HTTPS listener in one process: browsers on either see the same live state."""
    http_server = uvicorn.Server(http_config)
    https_server = uvicorn.Server(https_config)

    # Only the first server owns the signal handlers; Ctrl+C stops both.
    @contextlib.contextmanager
    def _noop_signals():
        yield

    https_server.capture_signals = _noop_signals
    original_handle_exit = http_server.handle_exit

    def handle_exit(sig, frame):
        https_server.should_exit = True
        original_handle_exit(sig, frame)

    http_server.handle_exit = handle_exit
    await asyncio.gather(http_server.serve(), https_server.serve())


def main():
    parser = argparse.ArgumentParser(description="Marshall Bittle X Main Server")
    parser.add_argument("--host", default="0.0.0.0", help="Bind host (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8000, help="Bind port (default: 8000)")
    parser.add_argument("--ssl-certfile", default=None, help="Path to TLS certificate (.pem) for HTTPS/WebXR")
    parser.add_argument("--ssl-keyfile", default=None, help="Path to TLS private key (.pem) for HTTPS/WebXR")
    parser.add_argument(
        "--https-port",
        type=int,
        default=None,
        help="Also serve HTTPS on this port (needs --ssl-certfile/--ssl-keyfile). Shares state with --port.",
    )
    args = parser.parse_args()

    if args.https_port:
        if not (args.ssl_certfile and args.ssl_keyfile):
            parser.error("--https-port needs --ssl-certfile and --ssl-keyfile")
        http_config = uvicorn.Config(app, host=args.host, port=args.port, log_level="info")
        https_config = uvicorn.Config(
            app,
            host=args.host,
            port=args.https_port,
            ssl_certfile=args.ssl_certfile,
            ssl_keyfile=args.ssl_keyfile,
            log_level="info",
        )
        asyncio.run(serve_http_and_https(http_config, https_config))
        return

    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        ssl_certfile=args.ssl_certfile,
        ssl_keyfile=args.ssl_keyfile,
        log_level="info",
    )


if __name__ == "__main__":
    main()
