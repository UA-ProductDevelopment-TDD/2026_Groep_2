# AGENTS.md: team UI/UX

Lees eerst de [`AGENTS.md`](../AGENTS.md) in de root voor het volledige project.

**Team:** Cas De Ryck, Tijs Gebruers.

## Doelgroep

Kinderen. De app moet speels zijn (Paw Patrol-look, Marshall de brandweerpup) en eenvoudig genoeg om zonder uitleg te gebruiken: grote knoppen, weinig tekst, duidelijke feedback.

## Taken

- **Besturing (actie 1, manueel):** livebeeld van de camera met een joystick om Marshall te sturen.
- **Blussen (actie 2, automatisch):** een knop "blussen". Marshall zoekt de vlam, zet zich in positie en spuit. Toon de voortgang (zoeken, positioneren, spuiten, klaar).
- **Feedback:** blafgeluid en een melding als het vuur uit is. Waterniveau en batterij altijd zichtbaar.
- **Noodstop:** een duidelijke stopknop.
- **VR-versie:** dezelfde app op de Meta Quest 3, met het camerabeeld als scherm in de 3D-ruimte en besturing via de controllers.

## Technologie

- **Vite + React + TypeScript**, met Tailwind CSS voor de stijl.
- **`nipplejs`** voor de joystick op het touchscreen.
- **React Three Fiber + `@react-three/xr`** voor de VR-modus. Op de Quest verschijnt een knop "Enter VR".
- Eén app voor gsm en Quest. De server serveert de gebouwde app (`vite build`) via HTTPS.

## Verbinding met de server

- De app praat **alleen met de server**, nooit rechtstreeks met de robot of de camera.
- Berichten: JSON over WSS op `wss://<laptop-ip>/ws`. Camerabeeld: `https://<laptop-ip>/stream`.
- Alle berichttypes staan in [`docs/interfaces.md`](../docs/interfaces.md). Verzin geen eigen berichten. Is er iets nodig dat er niet in staat, overleg dan met het Software-team en pas eerst dat bestand aan.
- Stuur joystickwaarden maximaal 10 keer per seconde.
- Werk zonder robot met nagebootste serverberichten (testmodus), zodat de UI los van de hardware ontwikkeld kan worden.

## Bestanden

Exporteer ontwerpen als PNG, SVG of PDF, zodat de andere teams ze zonder ontwerpprogramma kunnen bekijken. Zet links naar de bronbestanden (bv. Figma) erbij.

## Inspiratie

- **2025_Groep_2 (RobotDawg):** web-HUD met joystick en live camerabeeld.
- **Bittle_AI_voice:** blafgeluiden (`dist/sounds/bark.ogg`) en batterij-uitlezing.
