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
| `drive` | `x`, `y`: getal van -1 tot 1 | Joystickstand. `y` > 0 is vooruit, `x` > 0 is rechts. `0, 0` is stilstaan. Stuur maximaal 10 keer per seconde. |
| `extinguish` | — | Start de automatische blusroutine (actie 2). |
| `stop` | — | Noodstop: stilstaan, pomp uit, blusroutine afbreken. |

### Van server naar app

| `type` | Velden | Betekenis |
|---|---|---|
| `status` | `battery` (V), `water` (0–100 %), `connected` (`{ "biboard": bool, "camera": bool }`) | Elke seconde. |
| `fire` | `detected` (bool), `x` (-1 tot 1, positie in beeld), `temperature` (°C) | Resultaat van de warmtesensor. |
| `extinguish_state` | `state`: `searching`, `positioning`, `spraying`, `done`, `failed` | Voortgang van de blusroutine. |
| `fire_out` | — | Het vuur is uit: de app speelt het blafgeluid en toont een melding. |
| `thermal` | `width` (32), `height` (24), `data` (lijst met 768 temperaturen) | Optioneel, voor een warmtebeeld over de video. |

Voorbeelden:

```json
{ "type": "drive", "x": 0.4, "y": 0.8 }
{ "type": "extinguish" }
{ "type": "status", "battery": 7.4, "water": 60, "connected": { "biboard": true, "camera": true } }
{ "type": "fire", "detected": true, "x": -0.2, "temperature": 85.3 }
```

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
- De XIAO leest de MLX90640 via I2C en biedt de 32×24 temperaturen aan als JSON.
- Eindpunten en verversingsfrequentie: nog vast te leggen door het Software-team.
