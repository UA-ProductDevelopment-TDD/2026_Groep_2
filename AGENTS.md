# AGENTS.md: projectcontext voor AI-assistenten

Dit bestand geeft AI-tools (Claude Code, Antigravity, ...) en mensen de context van het project. Lees het volledig voor je code schrijft. Het meeste werk in deze repo gebeurt via vibe coding, dus volg de afspraken en interfaces hieronder strikt: verzin geen eigen protocol, pinnen of berichtformaten.

## Het project in het kort

Uitbreiding voor de **Petoi Bittle X** (vierpotige robothond, controller **BiBoard V1**), gemaakt voor het practicum Technology-Driven Design (Productontwikkeling, Universiteit Antwerpen, 2026-2027).

Thema: **Paw Patrol**. Bittle wordt **Marshall**, de brandweerpup. Het is een spelrobot voor kinderen, zodat ze vertrouwd raken met robots. Marshall zoekt een brand en "plast" die uit met water uit een tankje op zijn rug.

### Gedrag

1. **Actie 1, manueel: de brand zoeken.** Het kind bestuurt Marshall met een joystick op een gsm of een Meta Quest 3, en ziet live wat de camera op zijn kop ziet.
2. **Actie 2, automatisch: blussen.** Na een druk op de knop "blussen" zoekt Marshall de vlam met de warmtesensor, positioneert zich (de spuitmond zit tussen de achterpoten, dus hij moet zich omdraaien) en spuit water.
3. **Feedback** in de app: blafgeluid en melding als het vuur uit is, waterniveau en batterij.

Cyclus: patrouilleren, brand vinden, positioneren, plassen, verder patrouilleren.

Demo: een **echt theelichtje** in een niet-brandbare schaal, met een volwassene erbij.

## Systeemopbouw

```
BiBoard V1 (Bittle X) ──WiFi, WebSocket :81──┐
  pomp (via MOSFET), waterniveausensor       │
                                             ├── Server op laptop (Docker) ──HTTPS + WSS──┬── gsm-browser
XIAO ESP32-S3 Sense ──WiFi, MJPEG + data─────┘   Python, FastAPI                         └── Quest 3-browser (WebXR)
  camera + MLX90640-warmtesensor (I2C)
```

- **De server is de enige die met de robot en de camera praat.** De browsers praten alleen met de server. Reden: de Quest-browser en Safari op iOS ondersteunen geen Web Bluetooth, WebXR vereist HTTPS (de ESP32's spreken enkel `http`/`ws`), en een ESP32-camera kan maar 1 à 2 kijkers aan.
- **BiBoard: het "doen".** Lopen, de blus-pose, de pomp en het waterniveau. Aangestuurd met Petoi-commando's over de WiFi WebSocket die al in de OpenCat-firmware zit (`src/webServer.h` in de firmware-fork).
- **XIAO: het "zien".** Hij streamt beeld en warmtedata rechtstreeks naar de server, en deelt alleen voeding (5V/GND) met het BiBoard. Er is geen dataverbinding tussen XIAO en BiBoard.
- **Netwerk:** een eigen router of gsm-hotspot met vaste IP's (eduroam laat toestellen niet onderling praten).

Berichtformaten en poorten staan in [`docs/interfaces.md`](docs/interfaces.md). Pas je daar iets aan, doe dat dan eerst in dat bestand en daarna pas in de code.

## Technologie

| Onderdeel | Keuze |
|---|---|
| Server | Python, FastAPI + uvicorn, `websockets`, numpy, OpenCV; draait in Docker |
| Webapp | Vite + React + TypeScript; React Three Fiber + `@react-three/xr` voor VR; `nipplejs` voor de joystick; Tailwind CSS |
| BiBoard-firmware | Fork van OpenCat ESP32: [UA-ProductDevelopment-TDD/OpenCatEsp32-Quadruped-Robot](https://github.com/UA-ProductDevelopment-TDD/OpenCatEsp32-Quadruped-Robot) (Arduino IDE) |
| XIAO-firmware | Arduino (esp32-camera, een MLX90640-bibliotheek) |
| HTTPS lokaal | `mkcert`-certificaat met het LAN-IP van de laptop |

Achtergrond en redenen: [`docs/beslissingen.md`](docs/beslissingen.md). Onderdelen: [`docs/componenten.md`](docs/componenten.md).

## Teams en mappen

| Team | Map | Leden | Verantwoordelijkheid |
|---|---|---|---|
| Hardware | `hardware/` | Kauãn Steurs, Noah Ghoos | Helm, rugzak met watertank, spuitmond en slang, camerahouder, gewicht en zwaartepunt, waterdichtheid (3D-print) |
| Software / Elektronica | `software/` | Manu Fortems, Lukas Klink | Server, firmware (BiBoard en XIAO), camera en warmtesensor, pomp, voeding, blusbeweging |
| UI/UX | `ui-ux/` | Cas De Ryck, Tijs Gebruers | Webapp voor gsm en VR: livebeeld, joystick, knop "blussen", feedback, Paw Patrol-look voor kinderen |

"Software" en "Elektronica" zijn **hetzelfde team**; beide namen worden door elkaar gebruikt. Elke map heeft een eigen `AGENTS.md` met teamspecifieke context.

## Herbruikbare repo's van de cursus

Alle in de org [UA-ProductDevelopment-TDD](https://github.com/UA-ProductDevelopment-TDD):

- **Bittle_Studio**: Python-simulator (PyBullet) en Bluetooth-console. Gebruik het om de blus-pose te ontwerpen en te testen voor de echte robot. Exporteert naar `PetoiRobot`-scripts.
- **Bittle_URDF**: simulatiemodel van de Bittle X, om gewicht en zwaartepunt te testen.
- **OpenCatEsp32-Quadruped-Robot**: de firmware van het BiBoard. Bevat de WiFi WebSocket-server (poort 81) en de commando's `W` (pin schrijven) en `R` (pin lezen).
- **2025_Groep_2 (RobotDawg)**: lijkt sterk op dit project. Web-HUD met joystick en een MJPEG-stream van een XIAO ESP32-S3. Goed vertrekpunt voor de stream en de joystick.
- **Bittle_AI_voice**: Node-app met Petoi-commandobibliotheek, batterij-uitlezing (`P`-commando) en blafgeluiden.

## Afspraken

- **Taal:** documentatie in het Nederlands; code, variabelen en code-comments in het Engels.
- **Git:** werk nooit rechtstreeks op `main`. Branch per taak met de naam `<team>/<korte-beschrijving>`, daarna een pull request en een review. Zie [`CONTRIBUTING.md`](CONTRIBUTING.md).
- **De repo is publiek.** Commit nooit wachtwoorden, wifi-gegevens, IP-adressen of certificaten. Die staan in `.env` en `certs/`, en beide zijn genegeerd door Git.
- **De context-PDF (`TDD Presentatie Thema Template.pdf`) mag nooit in de repo.** Hij staat lokaal in `.git/info/exclude`.
- **Beslissingen:** leg elke nieuwe keuze vast in `docs/beslissingen.md`, met de reden erbij. Een AI moet een vastgelegde beslissing niet opnieuw in vraag stellen zonder dat te melden.
- **Open vragen:** staat iets op "nog te beslissen", vul het dan niet zelf in. Vraag het aan de gebruiker.
- **Veiligheid:** water en elektronica zitten dicht bij elkaar en de demo gebruikt een open vlam bij kinderen. Schakel de pomp altijd met een timeout uit, zodat hij nooit blijft lopen.

## Status (oktober 2026)

- Concept en architectuur liggen vast; er is nog geen code.
- Aanwezig: Bittle X met BiBoard V1, Meta Quest 3, een Grovekit (inhoud nog niet bekend).
- Te bestellen: XIAO ESP32-S3 Sense, MLX90640-BAB, pomp en toebehoren (zie `docs/componenten.md`).

### Nog te beslissen

- Welke uitgangspin op het BiBoard de pomp schakelt (eerst testen met een LED en het `W`-commando).
- Of de blusroutine een eigen firmware-commando wordt, of een reeks commando's vanaf de server.
- Welke onderdelen uit de Grovekit bruikbaar zijn.
- Het exacte maximumgewicht dat de Bittle X stabiel kan dragen.
