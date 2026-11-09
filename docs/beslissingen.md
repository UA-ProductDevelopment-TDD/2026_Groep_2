# Beslissingen

Elke belangrijke keuze, met de reden erbij. Nieuwe beslissingen komen onderaan. Wil je een beslissing terugdraaien, voeg dan een nieuwe regel toe in plaats van de oude te wissen.

| # | Datum | Beslissing | Reden |
|---|---|---|---|
| 1 | 2026-10-27 | Concept: Bittle wordt Marshall, de Paw Patrol-brandweerpup | Gekozen concept (concept 3) uit de themapresentatie |
| 2 | 2026-10-27 | Architectuur: robot en camera praten met een **server op een laptop**; gsm en Quest praten alleen met die server | De Quest-browser en iOS ondersteunen geen Web Bluetooth; WebXR vereist HTTPS, terwijl de ESP32's enkel `http`/`ws` spreken (mixed content); een ESP32-camera kan maar 1 à 2 kijkers aan |
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
| 17 | 2026-11-03 | Warmtesensor: **DFRobot MLX90614** in plaats van de MLX90640 (vervangt #7) | De sensor is al aanwezig en getest (werkt via I2C, adres 0x5A). Hij meet één temperatuur, wat volstaat voor een meter. De MLX90640 hoeft niet besteld te worden |
| 18 | 2026-11-03 | Geen warmtebeeld over de video; in de plaats een **branddetectiemeter** in de app die hoger staat naarmate de temperatuur hoger is | Eén temperatuurwaarde geeft geen beeld, maar wel een duidelijke meter. Voor kinderen is een meter eenvoudiger dan een warmtebeeld ("warm of koud" spelen) |
| 19 | 2026-11-09 | Meta Quest 2 VR-besturing & Thumbstick gang-mapping via `bittle_driver.py` | Intuïtieve kwadrant-sturing (vooruit, achteruit, links/rechts draaien, turbo draf met grip, en knoppen voor sit/stand/blushouding/zwaaien) conform de Bittle Studio catalogus (`catalog.js`). |
| 20 | 2026-11-09 | MLX90614 direct geïntegreerd in OpenCat-firmware met FreeRTOS `i2cBusMutex` & klokwisseling | Voorkomt dat de achtergrond-IMU-taak en de MLX90614 gelijktijdig de ESP32 I2C-bus benaderen (wat leidde tot `xQueueGenericSend queue.c:832` asserts). Schakelt tijdens MLX-lezen dynamisch naar 100 kHz SMBus en herstelt naar 400 kHz voor snelle gyro-sampling. |
| 21 | 2026-11-09 | Automatische IP-detectie van de hond via inkomende `POST /api/sensor` telemetrie | Zodra Marshall opstart en zijn warmtemeting naar de server stuurt, leest de server het client-IP uit en verbindt direct met `ws://<DOG_IP>:81` voor draadloze, kabelvrije besturing. |
| 22 | 2026-11-09 | Uitschakelen van Bluetooth (BLE en Classic SSP) in BiBoard OpenCat-firmware | Marshall wordt volledig via WiFi WebSocket bestuurd. Het deactiveren van dubbele Bluetooth-stacks spaart >80 KB RAM en voorkomt WiFi-radio interferentie en resets. |

## Nog te beslissen

- Of het blussen automatisch blijft, of een **aim assist** wordt: het kind stuurt en mikt zelf, de robot helpt onopvallend bij (bv. bijsturen naar de warmste richting), zodat het kind het gevoel heeft dat het zelf blust. Dit is waarschijnlijk de richting, maar nog niet beslist. Wordt het een aim assist, dan veranderen het bericht `extinguish` en de toestanden van `extinguish_state` in `docs/interfaces.md`.
- Welke uitgangspin op het BiBoard de pomp schakelt. Let op: GPIO 34–39 zijn alleen ingangen.
- Blusroutine als eigen firmware-commando, of als reeks commando's vanaf de server.
- Welke andere onderdelen uit de Grovekit bruikbaar zijn.
- De schaal van de branddetectiemeter, na tests met een theelichtje.
- Welke variant van de MLX90614 we hebben (BAA = 90°, DCC = 35°, DCI = 5° beeldhoek). Bij 90° helpt een geprint buisje om de beeldhoek te verkleinen.
- Maximaal gewicht op de Bittle X.
