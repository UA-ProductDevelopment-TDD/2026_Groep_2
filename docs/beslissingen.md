# Beslissingen

Elke belangrijke keuze, met de reden erbij. Nieuwe beslissingen komen onderaan. Wil je een beslissing terugdraaien, voeg dan een nieuwe regel toe in plaats van de oude te wissen.

| # | Datum | Beslissing | Reden |
|---|---|---|---|
| 1 | 2026-10-27 | Concept: Bittle wordt Marshall, de Paw Patrol-brandweerpup | Gekozen concept (concept 3) uit de themapresentatie |
| 2 | 2026-10-27 | Architectuur: robot en camera praten met een **server op een laptop**; gsm en Quest 3 praten alleen met die server | De Quest-browser en iOS ondersteunen geen Web Bluetooth; WebXR vereist HTTPS, terwijl de ESP32's enkel `http`/`ws` spreken (mixed content); een ESP32-camera kan maar 1 à 2 kijkers aan |
| 3 | 2026-10-27 | De server verbindt met het BiBoard via **WiFi WebSocket (poort 81)**, niet via Bluetooth | Zit al in de OpenCat-firmware; werkt vanuit Docker; BLE en WiFi tegelijk op de ESP32 is krap |
| 4 | 2026-10-27 | Camera: **Seeed XIAO ESP32-S3 Sense** | Klein en licht (zwaartepunt), goede WiFi; groep 2 van 2025 kreeg hem al werkend |
| 5 | 2026-10-27 | De XIAO streamt **rechtstreeks naar de server** en deelt alleen 5V/GND met het BiBoard | Alle logica draait op de server; een dataverbinding is niet nodig |
| 6 | 2026-10-27 | Demo-brand: een **echt theelichtje** in plaats van een LED-vlam | Geeft warmte af, dus warmtedetectie werkt |
| 7 | 2026-10-27 | Branddetectie: **MLX90640-BAB (55°)** op de XIAO via I2C, gecombineerd met het camerabeeld | Vindt de vlam via de echte temperatuur. 32×24 pixels volstaat op korte afstand. De 55°-versie heeft per graad dubbel zoveel resolutie als de 110°-versie. Het camerabeeld voorkomt dat een hand voor een vlam wordt aangezien |
| 8 | 2026-10-27 | Geen schakelbare IR-camera (dag/nacht) | Nabij-IR meet geen warmte en reageert ook op lampen en zonlicht |
| 9 | 2026-10-27 | Server in **Python met FastAPI** | WebSockets en HTTPS zitten erin; OpenCV en numpy voor detectie; sluit aan bij Bittle Studio (Python) |
| 10 | 2026-10-27 | Server draait in **Docker** | Dezelfde omgeving op elke laptop. Mogelijk omdat alles via WiFi gaat, niet via Bluetooth of USB |
| 11 | 2026-10-27 | Webapp in **Vite + React + TypeScript**, VR met **React Three Fiber + `@react-three/xr`** | Eén app voor gsm en Quest. AI-tools schrijven React goed; TypeScript vangt fouten op |
| 12 | 2026-10-27 | Berichten tussen app en server: **JSON over WSS**, vastgelegd in `docs/interfaces.md` | Teams en hun AI-tools schrijven code die op elkaar aansluit |
| 13 | 2026-10-27 | Pomp en waterniveau op het **BiBoard**; camera en warmtesensor op de **XIAO** | Het BiBoard "doet" (de pomp loopt synchroon met de blus-pose), de XIAO "ziet" |
| 14 | 2026-10-27 | Eerst prototypen met **Grove-modules**; in de eindversie Grove alleen waar gewicht, ruimte en water het toelaten | Grove is snel en zonder solderen, maar groter en minder waterdicht |
| 15 | 2026-10-27 | Documentatie in het Nederlands; code en comments in het Engels | Het project is Nederlandstalig; Engelse code is de norm |
| 16 | 2026-10-27 | AI-context in `AGENTS.md` (root en per team); `CLAUDE.md` verwijst ernaar | Het team gebruikt Claude Code en Antigravity; één bron van waarheid |

## Nog te beslissen

- Welke uitgangspin op het BiBoard de pomp schakelt. Let op: GPIO 34–39 zijn alleen ingangen.
- Blusroutine als eigen firmware-commando, of als reeks commando's vanaf de server.
- Hoe de joystick wordt omgezet naar Petoi-loopcommando's.
- Welke onderdelen uit de Grovekit bruikbaar zijn.
- Maximaal gewicht op de Bittle X.
