# AGENTS.md: team Software / Elektronica

Lees eerst de [`AGENTS.md`](../AGENTS.md) in de root voor het volledige project. "Software" en "Elektronica" zijn hetzelfde team.

**Team:** Manu Fortems, Lukas Klink.

## Taken

- **Server** (Python, FastAPI, in Docker): de enige verbinding met de robot en de camera. Hij zet app-berichten om naar Petoi-commando's, verdeelt het camerabeeld en detecteert de brand.
- **BiBoard-firmware** (fork van [OpenCatEsp32](https://github.com/UA-ProductDevelopment-TDD/OpenCatEsp32-Quadruped-Robot)): blus-pose, pomp en waterniveau.
- **XIAO ESP32-S3 Sense-firmware** (Arduino): MJPEG-stream en, als de sensor op de XIAO komt, de MLX90614 uitlezen via I2C.
- **Elektronica:** pomp via een MOSFET, buck-converter van 7,4 V naar 5 V, waterniveausensor, en alles afschermen tegen water.
- **Blusbeweging:** vlam vinden, omdraaien (de spuitmond zit achteraan), mikken, spuiten.

## Interfaces

Alle berichtformaten en poorten staan in [`docs/interfaces.md`](../docs/interfaces.md). Het UI-team bouwt daarop. Wijzig eerst dat bestand en dan pas de code, en laat het UI-team weten wat er veranderd is.

## Hardwarefeiten

- **BiBoard V1** = ESP32. De OpenCat-firmware heeft al een WiFi WebSocket-server op **poort 81** (`src/webServer.h`, met WiFiManager).
- Firmwarecommando's die we gebruiken: loopcommando's (`kwkF`, `kbalance`, ...), `P` (batterijspanning), `W` (pin schrijven), `R` (pin lezen). `W` en `R` worden **binair** verstuurd, zoals in Petoi's `ardSerial.py`.
- **GPIO 34, 35, 36, 39** (de analoge Grove-poorten, `ANALOG1–4` in `src/OpenCat.h`) zijn **alleen ingangen**. Gebruik ze voor de waterniveausensor, niet voor de pomp.
- De uitgangspin voor de pomp is nog niet gekozen. Kandidaten: de Grove-UART-pinnen (`UART_RX2`/`UART_TX2`) of een vrije servopoort. Test eerst met een LED.
- De XIAO deelt alleen 5V/GND met het BiBoard. Er is geen dataverbinding tussen beide.
- **Warmtesensor: DFRobot MLX90614** (beslissing #17), I2C-adres 0x5A. Hij geeft één temperatuur (gemiddeld over zijn beeldhoek) en de omgevingstemperatuur. Geen positie in beeld, dus geen warmtebeeld.
- De MLX90614 werkt officieel op maximaal 100 kHz (SMBus). Controleer elke uitlezing met de PEC-checksum, zoals in `tests/mlx90614_test/`.
- De server zet `temperature - ambient` om in `level` (0–100) voor de branddetectiemeter (zie `docs/interfaces.md`).

## Server in Docker

- Gebruik `docker-compose.yml` met `ports: "443:443"`.
- `.env` bevat `BIBOARD_IP` en `CAMERA_IP` (vaste IP's in de router). Commit dit bestand nooit.
- `certs/` bevat het `mkcert`-certificaat met het LAN-IP van de laptop, gekoppeld als volume. Commit dit nooit.
- mDNS-namen (`*.local`) werken niet vanuit de container. Gebruik IP-adressen.
- De server serveert ook de gebouwde webapp (`vite build`), zodat alles via één HTTPS-adres loopt.

## Veiligheid

- De pomp krijgt altijd een **timeout**, zowel in de firmware als op de server.
- Een `stop`-bericht of een verbroken verbinding betekent: stilstaan en de pomp uit.

## Openstaande punten van het prototype (review PR #4)

Bewust nog niet opgelost. Pak ze op voor het prototype de basis van de eindversie wordt.

**Veiligheid (voor de robot echt rondloopt bij kinderen):**

- Een verbroken `/ws`-verbinding stopt de robot niet en breekt de blusroutine niet af (`server/main.py`, `finally` van `ws_client`).
- Er is geen timeout op `drive` aan de serverkant: valt het `0, 0`-bericht weg, dan blijft de robot lopen.
- De D-pad in het dashboard stopt alleen bij `pointerup`, niet bij `pointerleave` of `pointercancel`.
- `action` stuurt elke willekeurige tekst rechtstreeks naar het BiBoard. Beter: een lijst met toegelaten commando's.
- `extinguish` stuurt meteen `kpee`, ook als de blusroutine al loopt.

**Kalibratie:**

- De branddetectiemeter gebruikt voorlopige waarden: volle uitslag bij +35 °C, drempel `detected` bij `level` 45 (server en dashboard). Vastleggen na tests met een theelichtje.

**Kleinere punten:**

- Pull-modus: de sensor wordt opgevraagd per stuk van 4 KB zolang `frame_seq % 10 == 0`, dus meerdere keren per frame, en dat houdt de stream op. De JPEG-parser loopt vast als er een `FFD9` vóór `FFD8` in de buffer staat.
- Bij `CAMERA_IP` gebruikt de server poort `8081` (de simulator). De CameraWebServer van de ESP32 streamt meestal op `:81/stream`.
- `except TimeoutError` rond `asyncio.wait_for` werkt pas vanaf Python 3.11. Zet de minimumversie in de README.
- `float(msg.get("x"))` zonder `try` sluit de WebSocket bij ongeldige invoer, en `x`/`y` worden niet begrensd op -1..1.
- Een trage VR-client vertraagt de camera-ingest, want frames worden na elkaar verstuurd.
- Afwijkingen van de afspraken, vast te leggen in `docs/beslissingen.md` of recht te zetten: geen Docker, poorten 8000/8443 in plaats van 443, en een `openssl`-certificaat in plaats van `mkcert`.
- In de code en de docs staat "Meta Quest 2"; we hebben een Quest 3.
- Three.js komt van unpkg (CDN) en werkt dus niet op een netwerk zonder internet.
- Het testdashboard (`server/static/`) overlapt met de webapp van het UI-team.
- De camerasimulator downloadt standaard een YouTube-video met `yt-dlp`. Beter is standaard `synthetic`.
- De scripts zijn bash (`hostname -I`, `.venv/bin`) en werken niet zomaar op Windows.
- Na te kijken op de hardware: of de WebSocket van OpenCat op poort 81 ruwe tekstcommando's zoals `kwkF` aanvaardt, zoals `bittle_driver.py` ze nu verstuurt.

## Hergebruik

- **Bittle Studio:** de blus-pose ontwerpen en testen in de simulator; export naar `PetoiRobot`-scripts.
- **2025_Groep_2:** code voor de MJPEG-stream van een XIAO ESP32-S3.
- **Bittle_AI_voice:** de Petoi-commandobibliotheek en de batterij-uitlezing.
