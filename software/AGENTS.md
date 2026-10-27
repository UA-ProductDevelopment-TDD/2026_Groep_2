# AGENTS.md: team Software / Elektronica

Lees eerst de [`AGENTS.md`](../AGENTS.md) in de root voor het volledige project. "Software" en "Elektronica" zijn hetzelfde team.

**Team:** Manu Fortems, Lukas Klink.

## Taken

- **Server** (Python, FastAPI, in Docker): de enige verbinding met de robot en de camera. Hij zet app-berichten om naar Petoi-commando's, verdeelt het camerabeeld en detecteert de brand.
- **BiBoard-firmware** (fork van [OpenCatEsp32](https://github.com/UA-ProductDevelopment-TDD/OpenCatEsp32-Quadruped-Robot)): blus-pose, pomp en waterniveau.
- **XIAO ESP32-S3 Sense-firmware** (Arduino): MJPEG-stream en de MLX90640 uitlezen via I2C.
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
- MLX90640: gebruik de **BAB-versie (55°)**. Op korte afstand (< 1 m) is een theelichtje een duidelijke hete plek. Combineer met het camerabeeld (een oranje, flikkerende vlek), zodat een hand niet als vlam wordt gezien.

## Server in Docker

- Gebruik `docker-compose.yml` met `ports: "443:443"`.
- `.env` bevat `BIBOARD_IP` en `CAMERA_IP` (vaste IP's in de router). Commit dit bestand nooit.
- `certs/` bevat het `mkcert`-certificaat met het LAN-IP van de laptop, gekoppeld als volume. Commit dit nooit.
- mDNS-namen (`*.local`) werken niet vanuit de container. Gebruik IP-adressen.
- De server serveert ook de gebouwde webapp (`vite build`), zodat alles via één HTTPS-adres loopt.

## Veiligheid

- De pomp krijgt altijd een **timeout**, zowel in de firmware als op de server.
- Een `stop`-bericht of een verbroken verbinding betekent: stilstaan en de pomp uit.

## Hergebruik

- **Bittle Studio:** de blus-pose ontwerpen en testen in de simulator; export naar `PetoiRobot`-scripts.
- **2025_Groep_2:** code voor de MJPEG-stream van een XIAO ESP32-S3.
- **Bittle_AI_voice:** de Petoi-commandobibliotheek en de batterij-uitlezing.
