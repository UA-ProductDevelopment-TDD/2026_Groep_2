# 2026_Groep_2: Bittle-uitbreiding

Een uitbreiding voor [Bittle](https://www.petoi.com/pages/bittle-open-source-bionic-robot-dog), de open-source vierpotige robot van Petoi.

## Teams

Het project is verdeeld over drie teams. Elk team beheert één map.

| Team | Map | Verantwoordelijkheid |
| --- | --- | --- |
| Hardware | [`hardware/`](hardware/) | Mechanisch en elektrisch ontwerp van de uitbreiding |
| Software | [`software/`](software/) | Firmware en code die de uitbreiding aanstuurt |
| UI/UX | [`ui-ux/`](ui-ux/) | Ontwerp van de gebruikersinterface van het programma |

## Samenwerken

- Commit niet rechtstreeks op `main`. Maak een branch aan en open een pull request.
- Geef branches de naam van je team en het werk, bijvoorbeeld `hardware/mount-bracket` of `software/sensor-driver`.
- Vraag iemand van je eigen team om een pull request te reviewen voordat je merget.
- Raakt een wijziging de map van een ander team? Vraag dan ook iemand van dat team om een review.
- Gebruik issues om taken en bugs bij te houden. Label elk issue met het team waartoe het behoort.

## Aan de slag

```sh
git clone https://github.com/UA-ProductDevelopment-TDD/2026_Groep_2.git
cd 2026_Groep_2
git checkout -b <team>/<korte-beschrijving>
```
