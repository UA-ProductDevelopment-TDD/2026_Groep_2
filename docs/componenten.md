# Componenten

Prijzen zijn grove schattingen. Werk de kolom "Status" bij zodra iets besteld of binnen is.

## Aanwezig

| Component | Rol |
|---|---|
| Petoi Bittle X met BiBoard V1 en batterij (2S, 7,4 V) | De robot; aangestuurd via WiFi (WebSocket, poort 81) |
| Meta Quest 3 | VR-bediening via de browser (WebXR) |
| Grovekit | Inhoud nog na te kijken (zie hieronder) |
| Laptop | Draait de server in Docker |
| Gsm's | Bediening via de browser |
| 3D-printer + filament | Helm, rugzak met tank, spuitmond, camerahouder |

## Na te kijken in de Grovekit

Zit een van deze onderdelen erin, dan hoeft het niet besteld te worden:

- Grove Thermal Imaging Camera (MLX90640, liefst de 55°-versie)
- Grove MOSFET (of een relais) voor de pomp
- Grove-kabels

Let op: een Grove "Water Sensor" detecteert druppels, maar meet het niveau in een tank slecht.

Heeft de kit een eigen bordje (Arduino of Seeeduino)? Dat is niet nodig: het BiBoard en de XIAO doen het werk al.

## Te voorzien

### Elektronica en sensoren

| Component | Voorstel | ± Prijs | Status | Opmerking |
|---|---|---|---|---|
| Camera | Seeed XIAO ESP32-S3 Sense | €15 | te bestellen | Streamt beeld en warmtedata over WiFi naar de server |
| Warmtesensor | MLX90640-**BAB** (55°) | €50–70 | te bestellen | Via I2C op de XIAO. Niet de 110°-versie (BAA) |
| 5V-voeding | Buck-converter 7,4 V naar 5 V (bv. Mini560) | €3 | te bestellen | Voedt de XIAO en de pomp vanuit de Bittle-batterij |
| Pompschakeling | Logic-level MOSFET-module + flyback-diode | €2 | te bestellen | Een GPIO kan een pomp niet rechtstreeks aansturen |
| Waterniveau | Contactloze sensor (bv. XKC-Y25) of 2 elektrodes in de tank | €1–5 | te bestellen | Op een analoge ingang van het BiBoard (GPIO 34–39) |
| Kabels | JST-/Dupont-connectoren, dunne siliconendraad, krimpkous | €5 | te bestellen | |

### Water

| Component | Voorstel | ± Prijs | Status | Opmerking |
|---|---|---|---|---|
| Pomp | Mini-pompje 3–5 V (dompel- of membraanpomp) | €3–8 | te bestellen | Zo licht mogelijk |
| Slangetje | Siliconen, Ø 3–4 mm | €3 | te bestellen | Van de tank naar de achterpoten |
| Tank | Zelf printen in PETG, of een klein flesje | — | te ontwerpen | Maximaal ±30–50 ml |
| Spuitmond | 3D-print of een dosseernaald | €1 | te ontwerpen | |
| Waterdicht maken | Conformal coating of siliconenkit | €5–10 | te bestellen | Voor de elektronica dicht bij het water |

### Netwerk en demo

| Component | Voorstel | ± Prijs | Status | Opmerking |
|---|---|---|---|---|
| Router | Reisrouter (bv. GL.iNet) of een gsm-hotspot | €0–30 | te bekijken | Vaste IP's. Eduroam werkt niet |
| Demo-brand | Theelichtjes + niet-brandbare schaal | €3 | te bestellen | |

## Aandachtspunten

- **Gewicht:** de Bittle X kan maar een beperkte last dragen. Tel alles samen (tank met water, pomp, XIAO, sensor, helm) en test eerst met gewichten. Gebruik Bittle_URDF en de simulator voor het zwaartepunt.
- **Batterij:** servo's, de camerastream (±300 mA) en de pomp hangen aan één batterij. Meet hoe lang Marshall kan spelen.
- **Pinnen op het BiBoard:** GPIO 34–39 (de analoge Grove-poorten) zijn alleen ingangen. Voor de pomp moet een vrije uitgang gezocht worden (Grove-UART of een vrije servopoort). Test eerst met een LED en het `W`-commando.
