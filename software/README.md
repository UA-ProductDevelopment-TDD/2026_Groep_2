# Software

Firmware and code that drives the add-on.

## Video Stream & WebXR Server Prototype

Quick prototype for testing WiFi camera video streaming into the main FastAPI server and out to both a 2D web browser and a Meta Quest 2 WebXR VR session.

### Components

- [`server/main.py`](server/main.py): Main FastAPI bridge server.
  - Accepts video streams over WiFi via **Push** (`WS /ws/camera` or `POST /api/camera/frame`) and **Pull** (`CAMERA_STREAM_URL` / `CAMERA_IP` multipart MJPEG).
  - Broadcasts live video to browsers via `GET /stream` (MJPEG), `GET /frame.jpg`, and binary WebSocket frames on `WS /ws`.
  - Implements the JSON WebSocket telemetry/control protocol from [`docs/interfaces.md`](../docs/interfaces.md) (`status`, `fire`, `drive`, `extinguish`, `stop`).
- [`server/bittle_driver.py`](server/bittle_driver.py): Robot driver translating joystick & VR controller inputs into Petoi OpenCat gaits based on **Bittle Studio** (`kwkF`, `ktrF`, `kwkL`, `kwkR`, `kbk`, `kbalance`, `ksit`, `kpee`, `khi`).
- [`server/static/index.html`](server/static/index.html): Web & WebXR (Three.js) application with a 2D MJPEG view, fire detection meter, manual drive controls, and an **"Enter VR"** mode for Meta Quest 2 featuring **intuitive walking** (thumbstick drive, grip turbo trot, A sit/stand, B/trigger extinguish pose, X wave, Y stop).
- [`camera_sim/simulator.py`](camera_sim/simulator.py): Simulated XIAO ESP32-S3 Sense camera + MLX90614 thermal sensor server.
  - Streams an animated Bittle POV with a flickering tea-light flame (or a webcam/video file via `--source 0` or `--source video.mp4`).
  - Both pushes frames to the main server (`ws://<server-ip>:8000/ws/camera`) and serves an ESP32-compatible MJPEG stream at `http://<sim-ip>:8081/stream`.

### Quick Start (One Command)

```sh
./software/run_prototype.sh
```

This automatically generates self-signed HTTPS certificates in `certs/` (required for WebXR on Meta Quest 2) and launches:
1. **Main Server (HTTP):** `http://<laptop-ip>:8000`
2. **Main Server (HTTPS for Meta Quest 2 WebXR):** `https://<laptop-ip>:8443`
3. **Camera Simulator:** `http://<laptop-ip>:8081/stream` (pushing live frames to the main server)

To run the camera simulator on another laptop/device over WiFi and stream to the main server:

```sh
software/.venv/bin/python software/camera_sim/simulator.py --push ws://<MAIN_SERVER_IP>:8000/ws/camera
```

---

## Heat sensor on the dog (BiBoard) -> dashboard over WiFi

[`firmware/bittle_heat_sensor/`](firmware/bittle_heat_sensor/bittle_heat_sensor.ino) reads the DFRobot MLX90614 (I2C 0x5A) on the BiBoard V1 and POSTs the readings to `POST /api/sensor` on the server. The dashboard (and VR) then shows the real temperature and fire meter, and the header badge says **Heat sensor: LIVE (MLX90614)**. A real sensor overrides the simulator's fake values automatically.

> **Warning:** this test sketch replaces the OpenCat firmware on the BiBoard. The dog will not walk until you flash OpenCat again (Petoi Desktop App, or the OpenCatEsp32 fork).

1. Plug the sensor into a **Grove I2C** port of the BiBoard (the I2C bus is GPIO21 SDA / GPIO22 SCL).
2. `cp software/firmware/bittle_heat_sensor/secrets.example.h software/firmware/bittle_heat_sensor/secrets.h` and fill in the WiFi name, password and the laptop IP (`hostname -I`). The dog needs a **2.4 GHz** network (on an iPhone hotspot: enable "Maximize Compatibility"). `secrets.h` is ignored by Git.
3. Compile and upload (the port is usually `/dev/ttyACM0` or `/dev/ttyUSB0`; check with `arduino-cli board list`):

```sh
arduino-cli compile -u -p /dev/ttyACM0 --fqbn esp32:esp32:esp32 software/firmware/bittle_heat_sensor
arduino-cli monitor -p /dev/ttyACM0 -c baudrate=115200
```

The serial monitor lists the I2C devices it finds (the MLX90614 shows up as `0x5A`), the dog's IP address and the server's HTTP status for every few readings.

---

## Tests

### `tests/mlx90614_test`

Reads the DFRobot MLX90614 heat sensor over I2C (address 0x5A) and prints the ambient and object temperature every 500 ms. Tested on an Arduino UNO R4 Minima with a Grove Base Shield; the sensor goes in an I2C port.

```sh
arduino-cli core install arduino:renesas_uno
arduino-cli compile -u -p /dev/ttyACM0 --fqbn arduino:renesas_uno:minima software/tests/mlx90614_test
arduino-cli monitor -p /dev/ttyACM0 -c baudrate=115200
```

On Linux, uploading first needs USB permissions: run `post_install.sh` from the `renesas_uno` core folder once with `sudo`.
