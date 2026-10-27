# AGENTS.md: team Hardware

Lees eerst de [`AGENTS.md`](../AGENTS.md) in de root voor het volledige project.

**Team:** Kauãn Steurs, Noah Ghoos.

## Taken

- **Marshall-pantser:** een helm en een rugzak met watertank, vastgeklikt op het frame van de Bittle X. Gemaakt met 3D-print.
- **Spuitmond en slangetje** tussen de achterpoten, om het vuur uit te "plassen".
- **Camerahouder op de kop**, met vrij zicht naast de helm. Daarop komen de XIAO ESP32-S3 Sense (camera) en de MLX90640-warmtesensor, die beide naar voren kijken.
- **Waterdichtheid:** bescherm de elektronica tegen het water uit de tank en de spuitmond.
- **Gewicht en zwaartepunt:** houd de tank zo klein en licht mogelijk (±30–50 ml) zodat Bittle stabiel blijft.

## Aandachtspunten

- De lens van de warmtesensor en de camera mag geen water krijgen. Ze zitten op de kop, ver van de spuitmond tussen de achterpoten.
- De pomp, de MOSFET, de buck-converter en de waterniveausensor moeten ook een plaats krijgen (zie [`docs/componenten.md`](../docs/componenten.md)).
- Print de tank in **PETG**: dat is beter waterdicht dan PLA.
- Test de lastverdeling eerst in simulatie met [Bittle_URDF](https://github.com/UA-ProductDevelopment-TDD/Bittle_URDF) en Bittle Studio, en daarna met gewichten op de echte robot.

## Bestanden

- Bewaar het originele CAD-bestand en exporteer ernaast een neutraal formaat (STEP of STL), zodat de andere teams het kunnen openen.
- Slicer-output (`.gcode`, `.bgcode`) en CAD-backups worden niet gecommit (zie `.gitignore`).
