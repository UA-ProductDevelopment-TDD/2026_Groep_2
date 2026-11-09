"""
Simulated XIAO ESP32-S3 Sense Camera + MLX90614 Heat Sensor Server.

Supports two streaming modes simultaneously:
1. PULL mode (ESP32 CameraWebServer style):
   - GET http://<sim-ip>:8081/stream  -> multipart/x-mixed-replace MJPEG stream
   - GET http://<sim-ip>:8081/sensor  -> JSON {"temperature": float, "ambient": float}
2. PUSH mode (active stream to main server over WiFi):
   - Connects to ws(s)://<server-ip>:<port>/ws/camera and pushes JPEG frames + thermal JSON.

Video sources:
- Default: Streams https://www.youtube.com/watch?v=iLoSsLU8bkk (cached at `software/camera_sim/video.mp4`).
- Any YouTube URL (`--source https://www.youtube.com/watch?v=...`): Downloads/caches with yt-dlp and loops it.
- Video file (`--source path/to/video.mp4`): Loops a local video file.
- Webcam (`--source 0`): Reads from local webcam index 0.
- Synthetic (`--source synthetic`): Animated Bittle Marshall POV with a virtual tea-light flame.
"""

import argparse
import asyncio
import json
import math
import subprocess
import sys
import time
from contextlib import asynccontextmanager
from pathlib import Path

import cv2
import numpy as np
import uvicorn
import websockets
from fastapi import FastAPI
from fastapi.responses import JSONResponse, StreamingResponse

DEFAULT_YOUTUBE_URL = "https://www.youtube.com/watch?v=iLoSsLU8bkk"
DEFAULT_CACHED_VIDEO = Path(__file__).parent / "video.mp4"


def resolve_video_source(source: str) -> str:
    """Resolve a YouTube URL (or default source) to a local MP4 file path, downloading via yt-dlp if needed."""
    if source == "synthetic" or source.isdigit():
        return source

    # If the default YouTube URL is used and video.mp4 is already downloaded, use it directly
    if source == DEFAULT_YOUTUBE_URL and DEFAULT_CACHED_VIDEO.exists():
        return str(DEFAULT_CACHED_VIDEO)

    if source.startswith(("http://", "https://")):
        target_path = DEFAULT_CACHED_VIDEO
        print(f"[CAMERA-SIM] Downloading video from {source} to {target_path} ...")
        cmd = [
            sys.executable,
            "-m",
            "yt_dlp",
            "-f",
            "bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/best[height<=480][ext=mp4]/best[ext=mp4]/best",
            "--merge-output-format",
            "mp4",
            "--force-overwrites",
            "-o",
            str(target_path),
            source,
        ]
        subprocess.run(cmd, check=True)
        return str(target_path)

    return source


class CameraSource:
    def __init__(self, source: str = DEFAULT_YOUTUBE_URL, fps: int = 30, width: int = 640, height: int = 480):
        self.source = source
        self.fps = fps
        self.width = width
        self.height = height
        self.cap: cv2.VideoCapture | None = None
        self.frame_count = 0
        self.start_time = time.time()

        # Simulated MLX90614 readings (degrees Celsius)
        self.ambient_temp = 22.5
        self.object_temp = 24.0

        resolved = resolve_video_source(source)
        if resolved != "synthetic":
            src = int(resolved) if resolved.isdigit() else resolved
            self.cap = cv2.VideoCapture(src)
            if not self.cap.isOpened():
                print(f"[WARN] Could not open video source '{resolved}', falling back to synthetic POV.")
                self.cap = None
            else:
                native_fps = self.cap.get(cv2.CAP_PROP_FPS)
                if native_fps and 5 <= native_fps <= 60:
                    self.fps = round(native_fps)
                print(f"[CAMERA-SIM] Loaded video source '{resolved}' ({self.width}x{self.height} @ {self.fps} FPS)")

    def next_frame(self) -> bytes:
        """Generate or capture the next frame and encode it as JPEG bytes."""
        self.frame_count += 1
        elapsed = time.time() - self.start_time

        # Simulate flame proximity oscillating over time so the fire meter moves naturally
        flame_proximity = 0.5 + 0.5 * math.sin(elapsed * 0.6)  # 0.0 (far) to 1.0 (close)
        noise = 0.3 * math.sin(elapsed * 7.3)
        self.ambient_temp = round(22.5 + 0.2 * math.sin(elapsed * 0.1), 2)
        self.object_temp = round(self.ambient_temp + 2.0 + flame_proximity * 38.0 + noise, 2)

        if self.cap is not None:
            ret, frame = self.cap.read()
            if not ret:
                # Loop video file when it reaches the end
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ret, frame = self.cap.read()
            if ret:
                frame = cv2.resize(frame, (self.width, self.height))
            else:
                frame = self._render_synthetic_frame(elapsed, flame_proximity)
        else:
            frame = self._render_synthetic_frame(elapsed, flame_proximity)

        ok, jpeg = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
        return jpeg.tobytes() if ok else b""

    def _render_synthetic_frame(self, elapsed: float, flame_proximity: float) -> np.ndarray:
        """Render a synthetic robot POV scene with an animated candle flame and HUD overlay."""
        h, w = self.height, self.width
        img = np.zeros((h, w, 3), dtype=np.uint8)

        img[: h // 2, :] = (32, 26, 22)
        img[h // 2 :, :] = (48, 42, 36)

        horizon_y = h // 2
        vanish_x = int(w // 2 + 40 * math.sin(elapsed * 0.8))
        for i in range(-6, 7):
            x_bottom = int(w // 2 + i * 110 + (elapsed * 60) % 110)
            cv2.line(img, (vanish_x, horizon_y), (x_bottom, h), (70, 62, 54), 1, cv2.LINE_AA)
        for row in range(1, 6):
            y = horizon_y + int((h - horizon_y) * (row / 5.0) ** 1.4)
            cv2.line(img, (0, y), (w, y), (65, 58, 50), 1)

        cx = int(w * 0.5 + math.sin(elapsed * 0.9) * (w * 0.22))
        cy = int(h * 0.58 + math.cos(elapsed * 0.45) * 25)
        scale = 0.6 + 0.7 * flame_proximity

        for radius, alpha in [(int(75 * scale), 0.15), (int(45 * scale), 0.3)]:
            overlay = img.copy()
            cv2.circle(overlay, (cx, cy - int(20 * scale)), max(4, radius), (0, 120, 255), -1, cv2.LINE_AA)
            cv2.addWeighted(overlay, alpha, img, 1 - alpha, 0, img)

        cup_w = int(34 * scale)
        cup_h = int(14 * scale)
        cv2.rectangle(img, (cx - cup_w, cy), (cx + cup_w, cy + cup_h), (175, 175, 180), -1, cv2.LINE_AA)
        cv2.ellipse(img, (cx, cy), (cup_w, int(6 * scale)), 0, 0, 360, (220, 220, 225), -1, cv2.LINE_AA)

        flicker_x = int(4 * math.sin(elapsed * 18.0))
        flicker_y = int(5 * math.cos(elapsed * 23.0))
        flame_h = int(42 * scale) + flicker_y
        flame_w = int(16 * scale)

        pts_outer = np.array(
            [
                [cx + flicker_x, cy - flame_h],
                [cx - flame_w, cy - int(flame_h * 0.25)],
                [cx, cy - 2],
                [cx + flame_w, cy - int(flame_h * 0.25)],
            ],
            np.int32,
        )
        cv2.fillPoly(img, [pts_outer], (0, 140, 255), cv2.LINE_AA)

        pts_inner = np.array(
            [
                [cx + flicker_x // 2, cy - int(flame_h * 0.75)],
                [cx - flame_w // 2, cy - int(flame_h * 0.22)],
                [cx, cy - 3],
                [cx + flame_w // 2, cy - int(flame_h * 0.22)],
            ],
            np.int32,
        )
        cv2.fillPoly(img, [pts_inner], (140, 245, 255), cv2.LINE_AA)

        cv2.rectangle(img, (0, 0), (w, 38), (18, 18, 24), -1)
        cv2.putText(
            img,
            f"XIAO ESP32-S3 SIM | {w}x{h} @ {self.fps}fps | Frame #{self.frame_count}",
            (12, 24),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.52,
            (220, 230, 240),
            1,
            cv2.LINE_AA,
        )
        return img


camera_source: CameraSource | None = None
push_target_url: str | None = None


async def push_loop(ws_url: str, cam: CameraSource):
    """Actively push JPEG frames + MLX90614 sensor readings to the main server over WebSocket."""
    interval = 1.0 / max(1, cam.fps)
    last_sensor_time = 0.0

    while True:
        try:
            print(f"[CAMERA-SIM] Connecting push stream to {ws_url} ...")
            async with websockets.connect(ws_url, max_size=4 * 1024 * 1024) as ws:
                print(f"[CAMERA-SIM] Connected! Streaming frames at {cam.fps} FPS to {ws_url}")
                while True:
                    t0 = time.monotonic()
                    jpeg = cam.next_frame()
                    if jpeg:
                        await ws.send(jpeg)

                    # Send thermal sensor reading 5 times per second
                    if t0 - last_sensor_time >= 0.2:
                        last_sensor_time = t0
                        await ws.send(
                            json.dumps(
                                {
                                    "type": "sensor",
                                    "temperature": cam.object_temp,
                                    "ambient": cam.ambient_temp,
                                }
                            )
                        )

                    elapsed = time.monotonic() - t0
                    await asyncio.sleep(max(0.005, interval - elapsed))
        except asyncio.CancelledError:
            break
        except (TimeoutError, websockets.exceptions.WebSocketException, OSError) as exc:
            print(f"[CAMERA-SIM] Push connection lost ({exc}). Retrying in 0.5s...")
            await asyncio.sleep(0.5)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    task = None
    if push_target_url and camera_source:
        task = asyncio.create_task(push_loop(push_target_url, camera_source))
    yield
    if task:
        task.cancel()


app = FastAPI(title="XIAO ESP32-S3 Sense Camera Simulator", lifespan=lifespan)


@app.get("/")
async def index():
    return {
        "service": "XIAO ESP32-S3 Sense Simulator",
        "source": camera_source.source if camera_source else None,
        "endpoints": {
            "mjpeg_stream": "/stream",
            "sensor_json": "/sensor",
        },
        "push_target": push_target_url,
    }


@app.get("/sensor")
async def get_sensor():
    """Return simulated MLX90614 object and ambient temperatures in Celsius."""
    assert camera_source is not None
    return JSONResponse(
        {
            "temperature": camera_source.object_temp,
            "ambient": camera_source.ambient_temp,
        }
    )


@app.get("/stream")
async def mjpeg_stream():
    """Serve an ESP32-compatible multipart MJPEG stream over HTTP."""
    assert camera_source is not None
    cam = camera_source
    interval = 1.0 / max(1, cam.fps)

    async def generate():
        while True:
            t0 = time.monotonic()
            jpeg = cam.next_frame()
            if jpeg:
                header = (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n"
                    b"Content-Length: " + str(len(jpeg)).encode() + b"\r\n\r\n"
                )
                yield header + jpeg + b"\r\n"
            elapsed = time.monotonic() - t0
            await asyncio.sleep(max(0.005, interval - elapsed))

    return StreamingResponse(
        generate(),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )


def main():
    global camera_source, push_target_url
    parser = argparse.ArgumentParser(description="XIAO ESP32-S3 Sense Camera + MLX90614 Simulator")
    parser.add_argument("--host", default="0.0.0.0", help="Bind host (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8081, help="Bind port (default: 8081)")
    parser.add_argument(
        "--source",
        default=DEFAULT_YOUTUBE_URL,
        help="Video source: YouTube URL (default: https://www.youtube.com/watch?v=iLoSsLU8bkk), local file path, webcam index ('0'), or 'synthetic'",
    )
    parser.add_argument("--fps", type=int, default=30, help="Target frame rate (default: 30)")
    parser.add_argument("--width", type=int, default=640, help="Frame width (default: 640)")
    parser.add_argument("--height", type=int, default=480, help="Frame height (default: 480)")
    parser.add_argument(
        "--push",
        default="ws://127.0.0.1:8000/ws/camera",
        help="Main server WebSocket URL to push frames to (set to '' to disable push mode)",
    )
    args = parser.parse_args()

    camera_source = CameraSource(source=args.source, fps=args.fps, width=args.width, height=args.height)
    push_target_url = args.push.strip() or None

    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
