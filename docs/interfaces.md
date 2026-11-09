# Interfaces

De afspraken over hoe de onderdelen met elkaar praten. Het UI-team en het Software-team schrijven hun code apart (vaak met AI), dus dit bestand is de enige bron van waarheid. Wijzig eerst dit bestand, en pas daarna de code aan beide kanten.

Status: **werkend prototype** (getest met Meta Quest 2, BiBoard V1, MLX90614 en server).

## Overzicht

| Verbinding | Protocol | Adres |
|---|---|---|
| Browser/VR naar server | HTTPS (webapp) + WSS (berichten) | `https://<laptop-ip>:8443/` en `wss://<laptop-ip>:8443/ws` |
| Browser naar camerabeeld | MJPEG via de server | `https://<laptop-ip>:8443/stream` |
| Server naar BiBoard | WebSocket (OpenCat-firmware) | `ws://<BIBOARD_IP>:81` (of seriële fallback `/dev/ttyACM0`) |
| BiBoard naar server | HTTP POST (warmtetelemetrie) | `http://<laptop-ip>:8000/api/sensor` (4 Hz) |
| Server naar XIAO | HTTP / WS (MJPEG-stream + warmtedata) | `http://<CAMERA_IP>:8081/stream` of `ws://<laptop-ip>:8000/ws/camera` |

De IP-adressen kunnen worden ingesteld via omgevingsvariabelen of `.env` (nooit committen):

```
BIBOARD_IP=172.20.10.4
BIBOARD_SERIAL_PORT=/dev/ttyACM0
CAMERA_IP=172.20.10.x
```
*Opmerking:* Indien `BIBOARD_IP` niet vooraf is ingesteld, ontdekt de server het IP-adres van de hond automatisch via inkomende telemetrie op `POST /api/sensor`!

## Browser en server (WSS, JSON)

Elk bericht is één JSON-object met een veld `type`.

### Van app naar server

| `type` | Velden | Betekenis |
|---|---|---|
| `drive` | `x`, `y`: getal van -1 tot 1; `turbo` (optioneel, bool) | Joystickstand. `y` > 0 is vooruit, `x` > 0 is rechts. `0, 0` is stilstaan. Stuur maximaal 10 keer per seconde. Met `turbo: true` draaft de robot (`ktrF`, ...) in plaats van te stappen. |
| `extinguish` | — | Start de automatische blusroutine (actie 2). |
| `stop` | — | Noodstop: stilstaan, pomp uit, blusroutine afbreken. |
| `action` | `command`: string (bijv. `ksit`, `kup`, `kpee`, `khi`, `kbalance`, of `toggle_sit`) | Direct Petoi-commando uitvoeren uit Bittle Studio. `toggle_sit` wisselt tussen zitten (`ksit`) en rechtstaan (`kup`). |
| `subscribe_frames` | `enabled` (bool, standaard `true`) | Optioneel. Vraagt de server om het camerabeeld ook als binaire JPEG-frames over deze WebSocket te sturen (voor de VR-textuur). Een client die dit niet stuurt, krijgt alleen JSON. |

### Van server naar app

| `type` | Velden | Betekenis |
|---|---|---|
| `status` | `battery` (V), `water` (0–100 %), `connected` (`{ "biboard": bool, "camera": bool }`); optioneel `fps` (beelden per seconde van de camera), `gait` en `gait_name` (huidige gang, zoals bij `robot_gait`) | Elke seconde. |
| `fire` | `detected` (bool), `level` (0–100), `temperature` (°C), `ambient` (°C), `source` (optioneel: `sensor`, `sim` of `none`) | Resultaat van de warmtesensor, minstens 2 keer per seconde. `level` stuurt de branddetectiemeter: hoe hoger de temperatuur, hoe hoger `level`. `detected` is `true` als `level` boven de drempel ligt. `source` zegt waar de waarde vandaan komt: `sensor` is de echte MLX90614, `sim` de camerasimulator, `none` nog geen meting. |
| `extinguish_state` | `state`: `searching`, `positioning`, `spraying`, `done`, `failed` | Voortgang van de blusroutine. |
| `fire_out` | — | Het vuur is uit: de app speelt het blafgeluid en toont een melding. |
| `robot_gait` | `gait` (code zoals `kwkF`, `ktrF`, `kbalance`), `name` (leesbare naam), `turbo` (bool) | Huidige gang van de robot naar aanleiding van joystick of knoppen. |

Voorbeelden:

```json
{ "type": "drive", "x": 0.4, "y": 0.8 }
{ "type": "extinguish" }
{ "type": "status", "battery": 7.4, "water": 60, "connected": { "biboard": true, "camera": true } }
{ "type": "fire", "detected": true, "level": 72, "temperature": 48.6, "ambient": 23.4 }
```

Binaire berichten op `/ws` zijn altijd JPEG-frames en komen alleen na `subscribe_frames`. Al het andere is JSON.

## Meta Quest 2 VR-besturing & Knoppenmapping

In de WebXR-omgeving (`https://<laptop-ip>:8443`):

| Controller / Input | Actie | Gang / Commando |
|---|---|---|
| **Thumbstick Y >= 0.25** | Vooruit lopen | `kwkF` |
| **Thumbstick Y >= 0.25 + X > 0.35** | Rechts afbuigen voorwaarts | `kwkR` |
| **Thumbstick Y >= 0.25 + X < -0.35** | Links afbuigen voorwaarts | `kwkL` |
| **Grip ingedrukt + Y >= 0.25** | Turbo draf vooruit / sturen | `ktrF`, `ktrR`, `ktrL` |
| **Thumbstick Y <= -0.25** | Achteruit stappen | `kbk` (`kbkR`, `kbkL`) |
| **Thumbstick \|Y\| < 0.25 & \|X\| > 0.30** | Ter plaatse draaien | `kwkR` / `kwkL` |
| **Deadzone (straal < 0.18)** | Stilstaan in balans | `kbalance` |
| **A-knop** | Zitten / Opstaan wisselen | `toggle_sit` (`ksit` / `kup`) |
| **B-knop / Trigger** | Blushouding (poot opheffen) | `kpee` |
| **X-knop** | Begroeten (pootje zwaaien) | `khi` |
| **Y-knop** | Noodstop / Balans herstellen | `kbalance` |

## Prototype-server (`software/server/main.py`)

- **Poorten:** HTTP op `8000` (browser, camera- en sensoringest) en HTTPS op `8443` (Meta Quest 2, WebXR). Beide delen dezelfde toestand.
- **Auto-Discovery:** Wanneer het BiBoard telemetrie post naar `/api/sensor`, detecteert de server het client-IP (`request.client.host`) en koppelt automatisch de achtergrond WebSocket `ws://<DOG_IP>:81`.
- **Endpoints van de server:**

| Endpoint | Richting | Inhoud |
|---|---|---|
| `GET /frame.jpg` | server naar browser | Het laatste camerabeeld als één JPEG (voor de WebGL-textuur). |
| `POST /api/camera/frame` | camera naar server | Body: één ruwe JPEG. Antwoord: `{ "ok": true, "seq": <volgnummer> }`, of `400` bij een lege body. |
| `WS /ws/camera` | camera naar server | Binaire berichten zijn JPEG-frames. Tekstberichten zijn JSON: `{ "type": "sensor", "temperature": <°C>, "ambient": <°C> }`. Gebruikt door de camerasimulator. |
| `POST /api/sensor` | sensor/BiBoard naar server | Zie \"Warmtesensor naar server\" hieronder. |

## Server en BiBoard

- De server gebruikt de bestaande Petoi-commando's over de WebSocket van de OpenCat-firmware (poort 81).
- Formaat: `{"type": "command", "taskId": "...", "commands": ["<gait>"]}` met fallback naar platte tekst strings.
- Joystick naar gang: de server zet `drive` om via `software/server/bittle_driver.py`. Commando's worden enkel verzonden wanneer de gang daadwerkelijk verandert om bus- en WiFi-congestie te voorkomen.

## Server en Warmtesensor (MLX90614)

De MLX90614 hangt aan de Grove I2C-poort van het BiBoard V1 (SDA = GPIO 21, SCL = GPIO 22).

- **Bus-synchronisatie:** De ESP32 IMU-taak (`taskIMU` op Core 0) en de sensor-loop delen dezelfde I2C-bus via een FreeRTOS `i2cBusMutex`.
- **Klok:** Tijdens de MLX90614 SMBus-uitlezing schakelt de firmware naar **100 kHz**, en keert daarna terug naar **400 kHz** voor de gyro.
- **Telemetrie:** Het BiBoard stuurt de metingen via HTTP-`POST` naar `http://<laptop-ip>:8000/api/sensor` (elke 250 ms = 4 Hz).
- Body: `{ "temperature": 48.6, "ambient": 23.4 }`, beide in °C. De server antwoordt `{ "ok": true, "level": 72 }`.
- **Branddetectiemeter (`level`):** De server berekent `level = min(100, round((delta / 35.0) * 100))` waarbij `delta = max(0, temperature - ambient)`. Vanaf level 45 wordt `fire_detected = true`.
