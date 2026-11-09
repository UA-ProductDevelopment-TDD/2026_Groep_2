"""
Bittle X Robot Driver & Gait Controller.

Translates intuitive joystick / VR thumbstick input (x, y, turbo) into Petoi OpenCat
gait and action commands based on Bittle Studio (catalog.js & bittle_link.py):
- `kwkF` / `ktrF`: walk / trot forward
- `kwkL` / `ktrL`: walk / trot left veer or pivot
- `kwkR` / `ktrR`: walk / trot right veer or pivot
- `kbk`  / `kbkL` / `kbkR`: walk backward / reverse veer
- `kbalance`: balanced standing stance (neutral stop)
- `ksit` / `kup`: sit down / stand up
- `kpee`: pee pose (Marshall's fire extinguishing stance)
- `khi`: wave hello

Dispatches commands over:
1. OpenCat WiFi WebSocket (`ws://<BIBOARD_IP>:81`)
2. Optional USB serial fallback (`/dev/ttyACM0` @ 115200 baud)
3. Simulated virtual robot fallback (when no hardware connection is active)
"""

import asyncio
import json
import logging
import math
import os
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import websockets

logger = logging.getLogger("bittle_driver")

# Motion catalog adapted from Bittle Studio (app/web/bittle-link/catalog.js)
MOTION_NAMES: dict[str, str] = {
    "kwkF": "Walk Forward",
    "kwkL": "Walk Left",
    "kwkR": "Walk Right",
    "ktrF": "Trot Forward (Turbo)",
    "ktrL": "Trot Left (Turbo)",
    "ktrR": "Trot Right (Turbo)",
    "kbk": "Walk Backward",
    "kbkL": "Reverse Left",
    "kbkR": "Reverse Right",
    "kbalance": "Balance (Stop)",
    "ksit": "Sit Down",
    "kup": "Stand Up",
    "kpee": "Pee Pose (Extinguish)",
    "khi": "Wave Hello",
    "krest": "Rest",
}


@dataclass
class DriveMapping:
    command: str
    name: str
    turbo: bool = False


def translate_joystick_to_gait(x: float, y: float, turbo: bool = False, deadzone: float = 0.18) -> DriveMapping:
    """
    Map continuous joystick input (x: -1 to 1 [left..right], y: -1 to 1 [backward..forward])
    to discrete OpenCat gait commands with intuitive steering quadrants.
    """
    mag = math.hypot(x, y)
    if mag < deadzone:
        return DriveMapping(command="kbalance", name=MOTION_NAMES["kbalance"], turbo=False)

    # Normalize within circle
    norm_x = max(-1.0, min(1.0, x / max(1.0, mag)))
    norm_y = max(-1.0, min(1.0, y / max(1.0, mag)))

    # 1. Forward motion (y >= 0.25)
    if norm_y >= 0.25:
        if norm_x > 0.35:
            cmd = "ktrR" if turbo else "kwkR"
        elif norm_x < -0.35:
            cmd = "ktrL" if turbo else "kwkL"
        else:
            cmd = "ktrF" if turbo else "kwkF"
        return DriveMapping(command=cmd, name=MOTION_NAMES.get(cmd, cmd), turbo=turbo)

    # 2. Reverse motion (y <= -0.25)
    if norm_y <= -0.25:
        if norm_x > 0.35:
            cmd = "kbkR"
        elif norm_x < -0.35:
            cmd = "kbkL"
        else:
            cmd = "kbk"
        return DriveMapping(command=cmd, name=MOTION_NAMES.get(cmd, cmd), turbo=False)

    # 3. Pivot in place (abs(y) < 0.25)
    if norm_x > 0.30:
        cmd = "kwkR"
    elif norm_x < -0.30:
        cmd = "kwkL"
    else:
        cmd = "kbalance"
    return DriveMapping(command=cmd, name=MOTION_NAMES.get(cmd, cmd), turbo=False)


class BittleDriver:
    """Manages the communication link and gait state for Petoi Bittle X (BiBoard V1)."""

    def __init__(
        self,
        biboard_ip: str | None = None,
        serial_port: str | None = None,
        on_gait_change: Callable[[DriveMapping], None] | None = None,
    ):
        self.biboard_ip = biboard_ip or os.getenv("BIBOARD_IP", "").strip() or None
        self.serial_port = serial_port or os.getenv("BIBOARD_SERIAL_PORT", "").strip() or None

        self.on_gait_change = on_gait_change
        self.current_mapping = DriveMapping("kbalance", MOTION_NAMES["kbalance"])
        self.is_sitting = False

        self._ws: Any | None = None
        self._serial = None
        self._connected = False
        self._ws_task: asyncio.Task | None = None
        self._keepalive_task: asyncio.Task | None = None
        self._last_cmd_time = 0.0

    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def current_gait(self) -> str:
        return self.current_mapping.command

    @property
    def current_gait_name(self) -> str:
        return self.current_mapping.name

    async def start(self) -> None:
        """Start background connection managers."""
        if self.biboard_ip:
            self._ws_task = asyncio.create_task(self._wifi_ws_loop())
        elif self.serial_port and os.path.exists(self.serial_port):
            self._init_serial()
        else:
            logger.info("BittleDriver running in simulation / virtual robot mode (no BiBoard IP configured).")

    def connect_ip(self, ip: str) -> None:
        """Dynamically attach or switch to BiBoard IP discovered via HTTP sensor telemetry."""
        clean_ip = ip.strip()
        if not clean_ip or clean_ip in ("127.0.0.1", "::1"):
            return
        if self.biboard_ip == clean_ip and self._ws_task and not self._ws_task.done():
            return
        self.biboard_ip = clean_ip
        if self._ws_task:
            self._ws_task.cancel()
        self._ws_task = asyncio.create_task(self._wifi_ws_loop())
        logger.info("BittleDriver auto-discovered dog at %s, starting WebSocket connection...", clean_ip)

    async def stop(self) -> None:
        """Stop connections and tasks."""
        if self._ws_task:
            self._ws_task.cancel()
        if self._ws:
            try:
                await self._ws.close()
            except (websockets.exceptions.WebSocketException, OSError):
                pass
        if self._serial:
            try:
                self._serial.close()
            except OSError:
                pass
        self._connected = False

    def _init_serial(self) -> None:
        """Try opening serial connection if pyserial is available."""
        try:
            import serial  # type: ignore

            self._serial = serial.Serial(self.serial_port, 115200, timeout=0.1)
            self._connected = True
            logger.info("Bittle connected via Serial on %s", self.serial_port)
        except OSError as exc:
            logger.warning("Could not open serial port %s: %s", self.serial_port, exc)
            self._serial = None

    async def _wifi_ws_loop(self) -> None:
        """Maintain persistent WebSocket connection to BiBoard on port 81."""
        url = f"ws://{self.biboard_ip}:81"
        while True:
            try:
                logger.info("Connecting to BiBoard at %s ...", url)
                async with websockets.connect(url, ping_interval=5.0, ping_timeout=5.0) as ws:
                    self._ws = ws
                    self._connected = True
                    logger.info("BiBoard WebSocket connected at %s", url)
                    # Send initial balance pose
                    await self.send_command("kbalance")
                    while True:
                        msg = await ws.recv()
                        logger.debug("BiBoard RX: %s", msg)
            except asyncio.CancelledError:
                break
            except (websockets.exceptions.WebSocketException, OSError) as exc:
                self._connected = False
                self._ws = None
                logger.debug("BiBoard connection error (%s). Reconnecting in 3s...", exc)
                await asyncio.sleep(3.0)

    async def send_command(self, cmd: str) -> None:
        """Send an OpenCat command (e.g. 'kwkF', 'kbalance', 'ksit') via WebSocket or Serial."""
        cmd_clean = cmd.strip()
        if not cmd_clean:
            return

        logger.info("Bittle TX -> %s (%s)", cmd_clean, MOTION_NAMES.get(cmd_clean, ""))

        # 1. Send via WebSocket if available (using OpenCat JSON command group format)
        if self._ws and self._connected:
            try:
                task_id = f"cmd_{int(time.monotonic() * 1000)}"
                json_payload = json.dumps({"type": "command", "taskId": task_id, "commands": [cmd_clean]})
                await self._ws.send(json_payload)
            except (websockets.exceptions.WebSocketException, OSError) as exc:
                logger.warning("BiBoard WS send failed: %s", exc)

        # 2. Send via Serial if available
        if self._serial and self._connected:
            try:
                self._serial.write(f"{cmd_clean}\n".encode("ascii"))
            except (OSError, RuntimeError) as exc:
                logger.warning("BiBoard Serial send failed: %s", exc)

    async def update_drive(self, x: float, y: float, turbo: bool = False) -> DriveMapping:
        """
        Update driving state from joystick (x, y) coordinates.
        Sends a command to the robot only when the gait changes, avoiding bus congestion.
        """
        mapping = translate_joystick_to_gait(x, y, turbo=turbo)

        # Update sitting state
        if mapping.command != "kbalance" and self.is_sitting:
            self.is_sitting = False

        if mapping.command != self.current_mapping.command or mapping.turbo != self.current_mapping.turbo:
            self.current_mapping = mapping
            await self.send_command(mapping.command)
            if self.on_gait_change:
                self.on_gait_change(mapping)

        return mapping

    async def execute_action(self, action: str) -> str:
        """Execute a discrete motion action (e.g. 'ksit', 'kup', 'kpee', 'khi', 'kbalance')."""
        cmd = action.strip()
        if cmd == "toggle_sit":
            cmd = "kup" if self.is_sitting else "ksit"
            self.is_sitting = not self.is_sitting

        self.current_mapping = DriveMapping(command=cmd, name=MOTION_NAMES.get(cmd, cmd))
        await self.send_command(cmd)
        if self.on_gait_change:
            self.on_gait_change(self.current_mapping)
        return cmd

    async def emergency_stop(self) -> None:
        """Immediate stop and balance."""
        await self.execute_action("kbalance")
