# Samenwerken aan 2026_Groep_2

Deze handleiding legt stap voor stap uit hoe je werk toevoegt aan het project. Je hebt geen ervaring met Git of GitHub nodig. Alles gebeurt met **GitHub Desktop**: je hoeft geen commando's te typen.

> **Werk je in een code-editor zoals VS Code of Zed?** Dan mag je dezelfde stappen ook daar doen. De volgorde en de afspraken blijven hetzelfde.

## Inhoud

1. [Even de begrippen](#1-even-de-begrippen)
2. [Eenmalig: installeren en instellen](#2-eenmalig-installeren-en-instellen)
3. [De werkcyclus](#3-de-werkcyclus)
4. [Een pull request reviewen](#4-een-pull-request-reviewen)
5. [Afspraken](#5-afspraken)
6. [Hulp, het ging mis](#6-hulp-het-ging-mis)

---

## 1. Even de begrippen

| Begrip | Wat het betekent |
| --- | --- |
| **Repository (repo)** | De projectmap met alle bestanden én hun volledige geschiedenis. |
| **`main`** | De officiële versie van het project. Hier werk je nooit rechtstreeks in. |
| **Branch** | Een eigen kopie van het project waarin je veilig kunt werken zonder anderen te storen. |
| **Commit** | Een opgeslagen tussenstap met een korte uitleg van wat je veranderd hebt. |
| **Push** | Je commits van je computer naar GitHub sturen. |
| **Pull** | De nieuwste versie van GitHub naar je computer halen. |
| **Pull request (PR)** | Een vraag aan het team: "Mag mijn branch in `main`?" Hier gebeurt de review. |
| **Merge** | Een branch samenvoegen met `main`. |
| **Issue** | Een taak of bug op GitHub. Elke stuk werk begint met een issue. |

---

## 2. Eenmalig: installeren en instellen

Dit doe je maar één keer.

1. **Installeer GitHub Desktop** via [desktop.github.com](https://desktop.github.com).
2. **Log in**: open GitHub Desktop en kies **Sign in to GitHub.com**.
3. **Stel je naam in**: ga naar **File → Options → Git** (op Mac: **GitHub Desktop → Settings → Git**) en vul je naam en het e-mailadres van je GitHub-account in.
4. **Haal de repo binnen**: kies **File → Clone repository**, zoek `UA-ProductDevelopment-TDD/2026_Groep_2`, kies een map op je computer en klik op **Clone**.

Je hebt nu het hele project op je computer staan.

---

## 3. De werkcyclus

Elke taak doorloopt dezelfde zes stappen. Daarna begin je weer bij stap 1.

```
Issue → Branch → Commits → Pull request → Review → Merge
```

### Stap 1: Zorg voor een issue

Ga op GitHub naar het tabblad **Issues**.

- Bestaat er al een issue voor je taak? Wijs het aan jezelf toe (**Assignees** rechts).
- Zo niet: klik op **New issue**, geef het een duidelijke titel (bijvoorbeeld *"Bevestigingsbeugel voor sensor ontwerpen"*), voeg het label van je team toe en wijs het aan jezelf toe.

Onthoud het nummer van het issue, bijvoorbeeld `#12`.

### Stap 2: Maak een branch

1. Kies in GitHub Desktop bovenaan bij **Current branch** voor `main`.
2. Klik op **Fetch origin** en daarna op **Pull origin**, als die knop verschijnt. Je hebt nu de nieuwste versie.
3. Klik op **Current branch → New branch**.
4. Geef de branch een naam volgens het patroon `team/korte-beschrijving`:
   - `hardware/sensor-beugel`
   - `software/sensor-driver`
   - `ui-ux/startscherm`
5. Klik op **Create branch**.

Alles wat je nu verandert, gebeurt in jouw branch. `main` blijft onaangeroerd.

### Stap 3: Werk en commit

Werk gewoon aan je bestanden in je eigen programma (CAD, Figma, editor…). GitHub Desktop toont in het tabblad **Changes** welke bestanden je veranderd hebt.

Een commit maak je zo:

1. Vink links de bestanden aan die bij deze stap horen.
2. Vul linksonder bij **Summary** een korte zin in over wat je gedaan hebt.
3. Klik op **Commit to `<jouw branch>`**.

**Goede commitboodschappen** zeggen wát je veranderd hebt:

| ✅ Goed | ❌ Niet goed |
| --- | --- |
| Gaten voor M3-schroeven toegevoegd | update |
| Afstandssensor uitgelezen via I2C | dingen gefixt |
| Kleuren startscherm aangepast aan huisstijl | wip |

**Commit vaak.** Elke keer dat een stukje af is, maak je een commit. Kleine stappen zijn makkelijker na te kijken en terug te draaien.

Klik daarna op **Publish branch** (de eerste keer) of **Push origin** (de keren daarna). Zo staat je werk ook op GitHub, en ben je het niet kwijt als je laptop crasht.

### Stap 4: Open een pull request

Is je taak af?

1. Klik in GitHub Desktop op **Create Pull Request**. Je browser opent GitHub.
2. Controleer dat er bovenaan **base: `main`** ← **compare: `jouw branch`** staat.
3. Geef de PR een duidelijke titel.
4. Schrijf in de beschrijving:
   - wat je veranderd hebt en waarom;
   - hoe iemand het kan controleren;
   - `Closes #12` (met het nummer van jouw issue). Dan sluit het issue vanzelf bij de merge.
5. Kies rechts bij **Reviewers** iemand van je eigen team. Raak je ook de map van een ander team? Voeg dan ook iemand van dat team toe.
6. Klik op **Create pull request**.

### Stap 5: Wacht op review en pas aan

De reviewer kan je PR goedkeuren of om aanpassingen vragen.

Moet je iets aanpassen? Blijf gewoon in dezelfde branch werken, commit en push opnieuw. De PR wordt automatisch bijgewerkt. Je hoeft geen nieuwe PR te openen.

### Stap 6: Merge en ruim op

Zodra de PR goedgekeurd is:

1. Klik op GitHub op **Merge pull request** en daarna op **Confirm merge**.
2. Klik op **Delete branch**. De branch heeft zijn werk gedaan.
3. Ga in GitHub Desktop terug naar `main` en klik op **Fetch origin** en **Pull origin**.
4. Verwijder je oude branch ook lokaal via **Branch → Delete**.

Klaar. Voor de volgende taak begin je weer bij [stap 1](#stap-1-zorg-voor-een-issue).

---

## 4. Een pull request reviewen

Iemand vraagt jou om te reviewen? Zo pak je het aan:

1. Open de PR op GitHub en lees de beschrijving.
2. Kijk in het tabblad **Files changed** wat er veranderd is. Bij een regel kun je op **+** klikken om een opmerking te plaatsen.
3. Klik op **Review changes** en kies:
   - **Approve**: alles in orde.
   - **Request changes**: er moet nog iets aangepast worden. Leg duidelijk uit wat.
   - **Comment**: alleen een vraag of opmerking.

Wees vriendelijk en concreet. Schrijf bijvoorbeeld *"De schroefgaten lijken 2 mm te klein voor M3, klopt dat?"* in plaats van *"dit klopt niet"*.

---

## 5. Afspraken

- **Nooit rechtstreeks op `main` werken.** Altijd via een branch en een pull request.
- **Eerst pullen, dan pas beginnen.** Haal altijd de nieuwste `main` binnen voor je een branch maakt.
- **Eén branch per taak.** Combineer geen ongerelateerde dingen in één PR.
- **Elke PR krijgt minstens één goedkeuring** van iemand anders voor hij gemerged wordt.
- **Blijf in je eigen map** (`hardware/`, `software/` of `ui-ux/`), tenzij je taak echt een andere map raakt. Vraag dan een review aan dat team.

### Let op met CAD-, ontwerp- en beeldbestanden

Bestanden zoals CAD-modellen, Figma-exports, PDF's en afbeeldingen kan Git **niet samenvoegen**. Werken twee mensen tegelijk aan hetzelfde bestand, dan moet één van beiden zijn werk weggooien.

Daarom:

- **Er werkt maar één persoon tegelijk aan zo'n bestand.**
- Zet in het issue welk bestand je aanpast, zodat anderen weten dat het "bezet" is.
- Twijfel je of iemand anders er ook aan werkt? Vraag het in de groepschat.

---

## 6. Hulp, het ging mis

### "Ik heb per ongeluk op `main` gewerkt"

Zolang je nog niet gecommit hebt, is er niets aan de hand:

1. Klik op **Current branch → New branch** en maak een nieuwe branch.
2. GitHub Desktop vraagt wat het met je wijzigingen moet doen. Kies **Bring my changes to `<nieuwe branch>`**.

Heb je al gecommit maar nog niet gepusht? Klik in het tabblad **History** met de rechtermuisknop op je commit en kies **Undo commit**. Je wijzigingen blijven bewaard. Volg daarna de stappen hierboven.

Heb je al naar `main` gepusht? Vraag hulp aan de beheerder van de repo.

### "Ik wil mijn laatste commit ongedaan maken"

Zolang hij nog niet gepusht is: klik op **Undo** onderaan links, of in **History** met de rechtermuisknop op de commit en kies **Undo commit**. Je wijzigingen staan dan terug in **Changes**.

### "Mijn branch loopt achter op `main`"

Anderen hebben intussen dingen gemerged. Haal die binnen in jouw branch:

1. Zorg dat je in je eigen branch zit.
2. Kies **Branch → Update from main**.
3. Push opnieuw.

### "Ik krijg een merge conflict"

Dat gebeurt als jij en iemand anders hetzelfde stuk van hetzelfde bestand veranderd hebben. Dat is normaal en niet erg.

- **Tekst- of codebestand**: GitHub Desktop toont de bestanden met een conflict. Klik op **Open in editor**. Je ziet dan iets als:

  ```
  <<<<<<< HEAD
  jouw versie
  =======
  de versie van de ander
  >>>>>>> main
  ```

  Hou wat juist is, verwijder de lijnen met `<<<<<<<`, `=======` en `>>>>>>>`, sla op en klik in GitHub Desktop op **Continue merge**.
- **CAD-, beeld- of ander binair bestand**: kies welke versie je houdt (**Use the modified file from…**) en overleg met de ander hoe jullie het werk combineren.

Twijfel je? Stop en vraag hulp. Een conflict verkeerd oplossen is erger dan even wachten.

### "Ik heb een bestand gewijzigd dat ik niet wou wijzigen"

Klik in **Changes** met de rechtermuisknop op het bestand en kies **Discard changes**. Let op: dit kun je niet ongedaan maken.

### Nog steeds vast?

Vraag het in de groepschat of open een issue met het label `vraag`. Iedereen is ooit begonnen. Er bestaan geen domme vragen.
