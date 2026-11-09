# Interfaces

De afspraken over hoe de onderdelen met elkaar praten. Het UI-team en het Software-team schrijven hun code apart (vaak met AI), dus dit bestand is de enige bron van waarheid. Wijzig eerst dit bestand, en pas daarna de code aan beide kanten.

Status: **voorstel**, nog niet getest op hardware.

## Overzicht

| Verbinding | Protocol | Adres |
|---|---|---|
| Browser naar server | HTTPS (webapp) + WSS (berichten) | `https://<laptop-ip>/` en `wss://<laptop-ip>/ws` |
| Browser naar camerabeeld | MJPEG via de server | `https://<laptop-ip>/stream` |
| Server naar BiBoard | WebSocket (OpenCat-firmware) | `ws://<BIBOARD_IP>:81` |
| Server naar XIAO | HTTP (MJPEG-stream + warmtedata) | `http://<CAMERA_IP>/...` (nog vast te leggen) |

De IP-adressen staan in `.env` (nooit committen):

```
BIBOARD_IP=192.168.x.x
CAMERA_IP=192.168.x.x
```

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

## Prototype-server (`software/server/main.py`)

Het prototype wijkt op een paar punten af van het overzicht hierboven. Dit is voorlopig; de eindversie draait in Docker op HTTPS-poort 443.

- **Poorten:** HTTP op `8000` (browser, camera- en sensoringest) en HTTPS op `8443` (Quest, WebXR). Beide delen dezelfde toestand.
- **Extra endpoints van de server:**

| Endpoint | Richting | Inhoud |
|---|---|---|
| `GET /frame.jpg` | server naar browser | Het laatste camerabeeld als één JPEG (voor de WebGL-textuur). |
| `POST /api/camera/frame` | camera naar server | Body: één ruwe JPEG. Antwoord: `{ "ok": true, "seq": <volgnummer> }`, of `400` bij een lege body. |
| `WS /ws/camera` | camera naar server | Binaire berichten zijn JPEG-frames. Tekstberichten zijn JSON: `{ "type": "sensor", "temperature": <°C>, "ambient": <°C> }`. Gebruikt door de camerasimulator. |
| `POST /api/sensor` | sensor naar server | Zie "Warmtesensor naar server" hieronder. |

- **Pull-modus:** zonder camera die zelf beelden pusht, haalt de server de MJPEG-stream op van `CAMERA_STREAM_URL` (en de warmtedata van `CAMERA_SENSOR_URL`). Met alleen `CAMERA_IP` gebruikt hij `http://<CAMERA_IP>:8081/stream` en `/sensor`, de adressen van de simulator.

## Server en BiBoard

- De server gebruikt de bestaande Petoi-commando's over de WebSocket van de OpenCat-firmware (poort 81).
- Joystick naar gang: de server zet `drive` om in Petoi-loopcommando's (`kwkF`, `kwkL`, `kwkR`, `kbk`, `kbalance`, ...). De exacte mapping legt het Software-team vast na het testen.
- Batterij: het `P`-commando. Het antwoord heeft de vorm `Voltage: 7.42 V`.
- Pomp: het `W`-commando (pin schrijven, binair verstuurd zoals Petoi's `ardSerial.py` dat doet). De pin is nog te bepalen.
- Waterniveau: het `R`-commando op een analoge ingang (GPIO 34, 35, 36 of 39). Nog te bepalen welke.
- **De pomp moet altijd een timeout hebben**, zodat hij nooit blijft lopen als de verbinding wegvalt.

Nog te beslissen: of de blusroutine een eigen firmware-commando wordt, of een reeks commando's die de server stuurt.

## Server en XIAO

- De XIAO serveert een MJPEG-stream over HTTP.
- De MLX90614 geeft twee waarden: `temperature` (wat de sensor ziet) en `ambient` (de temperatuur van de sensor zelf), allebei in °C.
- Het bord met de sensor biedt die twee waarden aan; de server rekent `level` uit. Op welk bord de sensor komt, is nog te beslissen.

### Warmtesensor naar server (proefopstelling)

Voor de test hangt de MLX90614 aan het BiBoard (Grove I2C-poort). Dit beslist niet op welk bord de sensor definitief komt (zie `docs/beslissingen.md`).

- Het BiBoard stuurt de metingen met een HTTP-`POST` naar `http://<laptop-ip>:8000/api/sensor`, ongeveer 4 keer per seconde.
- Body: `{ "temperature": 48.6, "ambient": 23.4 }`, beide in °C. De server antwoordt `{ "ok": true, "level": 72 }`, of `400` bij ongeldige of onmogelijke waarden.
- Zolang de server in de laatste 3 seconden echte metingen kreeg, negeert hij de nagebootste waarden van de camerasimulator.

### Branddetectiemeter (`level`)

- De server rekent `level` uit het verschil `temperature - ambient`: 0 bij geen verschil, 100 bij het verschil van een theelichtje van dichtbij. Daartussen loopt de meter mee.
- Het verschil van een vol theelichtje en de drempel voor `detected` worden vastgelegd na tests. Tot dan: nog te bepalen.
- Eindpunten en verversingsfrequentie: nog vast te leggen door het Software-team.
