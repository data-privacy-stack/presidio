# DatOnym: Aenderungsdokumentation gegenueber Presidio

Diese Dokumentation beschreibt, was im Fork `thomas-lauer/DatOnym` gegenueber
dem Originalprojekt `data-privacy-stack/presidio` geaendert oder ergaenzt wurde.

Stand dieser Dokumentation: Branch `feature/de-prompt-gateway`, Version der
oeffentlichen Webapp `0.5`.

## Kurzfassung

DatOnym erweitert Presidio um drei neue Schichten:

1. Ein deutsches Analyzer-Profil fuer Presidio.
2. Ein FastAPI-Gateway fuer reversible Prompt-Anonymisierung vor LLM-Aufrufen.
3. Eine statische Browser-Testwebapp fuer manuelle Prompt-Anonymisierung und
   Rueckpersonalisierung.

Die bestehenden Presidio-Module wurden nicht strukturell umgebaut. Die Arbeit
ist additiv angelegt: neue Dateien, neue Konfigurationen, neue Gateway- und
Webapp-Komponenten.

## Repository- und Produktanpassungen

### Fork und Name

- Original: `data-privacy-stack/presidio`
- Fork: `thomas-lauer/DatOnym`
- Produktname: `DatOnym`
- Oeffentliche Testwebapp: `datOnym`
- Technische Python-Paketnamen bleiben lowercase, z. B. `datonym_gateway`.

### Git-Remotes

- `origin`: `https://github.com/thomas-lauer/DatOnym.git`
- `upstream`: `https://github.com/data-privacy-stack/presidio.git`

### Branches

- Entwicklungsbranch: `feature/de-prompt-gateway`
- GitHub-Pages-Branch: `gh-pages`

## Was am Presidio-Original unveraendert blieb

Die Kernpakete von Presidio bleiben erhalten:

- `presidio-analyzer`
- `presidio-anonymizer`
- `presidio-image-redactor`
- `presidio-structured`
- `presidio-cli`
- vorhandene Presidio-Dokumentation, Tests und Beispielstruktur im Hauptbranch

Es wurden keine bestehenden Presidio-Analyzer- oder Presidio-Anonymizer-Klassen
direkt umgeschrieben. DatOnym nutzt Presidio als Engine und fuegt eigene
Konfiguration, Operatoren, Gateway-Logik und Weboberflaechen hinzu.

## Neues deutsches Analyzer-Profil

Neue Datei:

- `presidio-analyzer/presidio_analyzer/conf/datonym_de_analyzer.yaml`

Ziel:

- Presidio fuer deutschsprachige Prompt-Anonymisierung vorkonfigurieren.
- Deutsche Recognizer aktivieren, die im Presidio-Umfeld vorhanden sind, aber
  nicht immer im Standardprofil aktiv genutzt werden.
- Deutsche NLP-Erkennung ueber spaCy `de_core_news_md` verwenden.

Wichtige Einstellungen:

- `supported_languages: [de]`
- NLP-Modell: `de_core_news_md`
- Score-Schwelle: `0.35`
- Telefonregionen: `DE`, `AT`, `CH`, `LU`

Aktivierte globale Entity-Typen:

- `PERSON`
- `LOCATION`
- `ORGANIZATION`
- `EMAIL_ADDRESS`
- `PHONE_NUMBER`
- `IBAN_CODE`
- `CREDIT_CARD`
- `IP_ADDRESS`
- `URL`
- `DATE_TIME`

Aktivierte deutsche Recognizer:

- `DE_TAX_ID`
- `DE_TAX_NUMBER`
- `DE_PASSPORT`
- `DE_ID_CARD`
- `DE_SOCIAL_SECURITY`
- `DE_HEALTH_INSURANCE`
- `DE_KFZ`
- `DE_HANDELSREGISTER`
- `DE_PLZ`
- `DE_LANR`
- `DE_BSNR`
- `DE_VAT_ID`
- `DE_FUEHRERSCHEIN`

## Neues DatOnym Gateway

Neuer Ordner:

- `datonym-gateway/`

Ziel:

Ein OpenAI-kompatibles Gateway, das Prompts vor dem LLM anonymisiert und die
LLM-Antwort danach wieder rueckpersonalisiert.

### Gateway-Dateien

- `datonym-gateway/pyproject.toml`
- `datonym-gateway/.env.example`
- `datonym-gateway/README.md`
- `datonym-gateway/datonym_gateway/__init__.py`
- `datonym-gateway/datonym_gateway/app.py`
- `datonym-gateway/datonym_gateway/config.py`
- `datonym-gateway/datonym_gateway/models.py`
- `datonym-gateway/datonym_gateway/operators.py`
- `datonym-gateway/datonym_gateway/presidio.py`
- `datonym-gateway/datonym_gateway/service.py`
- `datonym-gateway/datonym_gateway/tokens.py`

### API-Endpunkte

Neu bereitgestellt:

- `GET /healthz`
- `POST /v1/anonymize`
- `POST /v1/chat/completions`
- `GET /demo`
- `POST /demo/anonymize`

`/v1/chat/completions` orientiert sich am OpenAI-Chat-Completions-Format. Das
Gateway anonymisiert alle stringbasierten `messages[].content`-Werte,
leitet den Request an ein LLM weiter und ersetzt bekannte DatOnym-Tokens in
der Antwort wieder durch die Originalwerte.

### LLM-Forwarding

Konfigurierbar ueber Umgebungsvariablen:

- `LLM_BASE_URL`
- `LLM_API_KEY`
- `OPENAI_API_KEY`
- `LLM_MODEL_DEFAULT`
- `DATONYM_ANALYZER_CONFIG`
- `DATONYM_LANGUAGE`
- `DATONYM_SCORE_THRESHOLD`
- `DATONYM_REQUEST_TIMEOUT_SECONDS`

Standardverhalten:

- OpenAI-kompatibler Zielpfad: `/v1/chat/completions`
- kein Streaming im MVP
- keine Tool Calls
- keine Bildinhalte
- keine Datei- oder Multimodal-Inhalte

## Reversible Tokenisierung

Neue Datei:

- `datonym-gateway/datonym_gateway/tokens.py`

DatOnym ersetzt erkannte personenbezogene Daten durch stabile Tokens:

```text
#DATONYM_PERSON_0001#
#DATONYM_EMAIL_ADDRESS_0001#
#DATONYM_IBAN_CODE_0001#
```

Eigenschaften:

- Tokens sind pro Request stabil.
- Gleicher Originalwert plus Entity-Typ bekommt im selben Request denselben
  Token.
- Das Mapping wird nur im RAM gehalten.
- Es gibt keine Persistenz des Mappings.
- Produktionsendpunkte geben Originalwerte nicht zurueck.
- Die Rueckpersonalisierung ersetzt nur bekannte Tokens aus dem aktuellen
  Request-Mapping.

### Kollisionserkennung im Gateway

Das Gateway lehnt Eingaben ab, die bereits wie DatOnym-Tokens aussehen. Dadurch
wird verhindert, dass Nutzereingaben absichtlich oder versehentlich mit dem
Rueckersetzungsformat kollidieren.

Hinweis: Die statische Browser-Webapp verhaelt sich anders. Dort werden bereits
vorhandene DatOnym-Tokens toleriert, weil sie fuer manuelle Tests und
mehrstufige Beispieltexte gebraucht werden.

## Custom Presidio Operatoren

Neue Datei:

- `datonym-gateway/datonym_gateway/operators.py`

Enthaelt:

- `DatonymTokenAnonymizer`
- `DatonymTokenDeanonymizer`

Der Anonymizer erzeugt Tokens aus dem request-lokalen Mapping. Die eigentliche
Rueckpersonalisierung der LLM-Antwort erfolgt im Gateway ueber das Mapping,
weil die Antwort vom LLM keine originalen Presidio-Spans mehr enthaelt.

## Service- und Gateway-Ablauf

Der zentrale Ablauf in `datonym-gateway/datonym_gateway/service.py`:

1. Request kommt an.
2. Pro Request wird ein neues `DatonymMapping` erzeugt.
3. Jede Chat-Nachricht wird mit Presidio analysiert.
4. Presidio-Anonymizer ersetzt erkannte Werte mit DatOnym-Tokens.
5. Der anonymisierte Request wird an das LLM gesendet.
6. Die Antwort wird kopiert.
7. Bekannte Tokens in Antwortfeldern werden zurueckersetzt.
8. Der Client erhaelt die personalisierte Antwort.
9. Das Mapping faellt nach Request-Ende weg.

Unterstuetzte Antwortfelder fuer Rueckersetzung:

- `choices[].message.content`
- `choices[].delta.content`
- `choices[].text`

## Datenschutzentscheidungen im Gateway

Das Gateway wurde so gebaut, dass Originalwerte moeglichst nicht austreten:

- Originalwerte werden nicht geloggt.
- Originalwerte werden nicht persistiert.
- `/v1/anonymize` gibt nur anonymisierten Text, Entity-Metadaten und Tokenanzahl
  zurueck.
- Fehlerantworten enthalten keine Originalwerte.
- Mapping lebt nur pro Request im RAM.

Ausnahme:

- `/demo/anonymize` zeigt Originalwerte im Mapping an. Dieser Endpoint ist nur
  fuer lokale Inspektion gedacht und wird im README entsprechend markiert.

## Lokale Gateway-Demo

Neue statische Dateien im Gateway:

- `datonym-gateway/datonym_gateway/static/index.html`
- `datonym-gateway/datonym_gateway/static/styles.css`
- `datonym-gateway/datonym_gateway/static/app.js`

Ziel:

- Lokale visuelle Pruefung der Gateway-Anonymisierung unter `/demo`.
- Anzeige von anonymisiertem Text, Mapping und erkannten Entitaeten.
- Manuelle Rueckersetzung einer Antwort mit Tokens.

Wichtig:

- Diese lokale Demo verwendet den FastAPI-Demo-Endpoint.
- Sie ist nicht die oeffentliche GitHub-Pages-Webapp.

## Oeffentliche statische Webapp

Neuer Ordner:

- `webapp/`

Dateien:

- `webapp/.nojekyll`
- `webapp/README.md`
- `webapp/index.html`
- `webapp/styles.css`
- `webapp/app.js`

Oeffentliche URL:

- `https://thomas-lauer.github.io/DatOnym/`

GitHub-Pages-Branch:

- `gh-pages`

### Zweck der Webapp

Die Webapp ist ein reines Browser-Testwerkzeug:

1. Prompt eingeben.
2. Button `Anonymisieren` klicken.
3. Anonymisierten Prompt kopieren.
4. Prompt manuell in einen LLM-Chat einfuegen.
5. LLM-Antwort in das zweite Textfeld einfuegen oder per Drag and Drop ablegen.
6. Button `Personalisieren` klicken.
7. DatOnym-Tokens werden wieder durch Originalwerte ersetzt.

### Datenschutz der Webapp

Die Webapp ist statisch und laeuft im Browser:

- Es gibt keinen eigenen DatOnym-Backendserver.
- Promptdaten werden nicht an DatOnym gesendet.
- Antwortdaten werden nicht an DatOnym gesendet.
- Mappingdaten werden nicht an DatOnym gesendet.
- Es wird kein lokaler Seitenaufrufzaehler mehr verwendet.
- Es wird kein `localStorage` fuer Mapping oder Prompts verwendet.

Hinweis in der UI:

- "Diese Webseite speichert keine eingegebenen Prompt-, Antwort- oder
  Mappingdaten."

Verantwortlich:

- `www.lauer.io`

Version:

- `0.5`

## Browser-Webapp-Erkennung

Die oeffentliche Webapp nutzt keine Presidio-Laufzeit im Browser. Sie enthaelt
stattdessen kompakte JavaScript-Recognizer fuer die manuelle Testnutzung.

Erkannte Kategorien:

- `PERSON`
- `EMAIL_ADDRESS`
- `PHONE_NUMBER`
- `IBAN_CODE`
- `CREDIT_CARD`
- `IP_ADDRESS`
- `URL`
- `DATE_TIME`
- `ORGANIZATION`
- `LOCATION`
- `DE_PLZ_LOCATION`
- `ADDRESS`
- `DE_TAX_ID`

### Personen

Erkannte Beispiele:

- `Herr Peter Mustermann`
- `Herrn Peter Mustermann`
- `Frau Erika Musterfrau`
- `Name: Peter Mustermann`
- `Name ist Peter Mustermann`
- `ich bin Peter Mustermann`

Wenn derselbe Name mehrfach vorkommt, wird derselbe Token wiederverwendet:

```text
Herrn #DATONYM_PERSON_0001#
Name: #DATONYM_PERSON_0001#
```

### Adressen

Erkannte Beispiele:

```text
12345 Musterstadt, Beispielstrasse 1
```

und mehrzeilig:

```text
54321 Beispielort-Musterteil,
Musterweg 2
```

Ebenfalls beruecksichtigt:

- Ortsnamen mit Klammerzusatz, z. B. `Musterstadt (Region)`
- Ortsteile mit Bindestrich
- Schreibweisen wie `Musterort a. d. Beispiel`

### Bereits vorhandene DatOnym-Tokens

Die Webapp kann Texte verarbeiten, die bereits DatOnym-Tokens enthalten. Diese
Tokens bleiben stehen. Neue Tokens zaehlen ab dem hoechsten vorhandenen Index
weiter.

Beispiel:

```text
#DATONYM_DATE_TIME_0001#
```

bleibt bestehen; ein neu erkanntes Datum kann dann z. B. als
`#DATONYM_DATE_TIME_0002#` erzeugt werden.

## Beispieltext der Webapp

Der Beispielbutton setzt folgenden Prompt:

```text
Bitte erstelle mir eine eMail an Herrn Peter Mustermann.
Ich moechte seine Persoenlichen Daten mit Ihm abgleichen

Name: Peter Mustermann
Geburtstag: 12.12.2012
IBAN: DE999999000099990000
Telefonnummer: 0777/889988
Ihre IP-Adresse Lautet: 172.172.8.1
```

Hinweis: Im Source-Code koennen Umlaute je nach Anzeigeumgebung escaped oder
anders dargestellt werden. Die Webapp wird im Browser als UTF-8 ausgeliefert.

## Entfernte oder bewusst nicht umgesetzte Punkte

### Entfernt

- Button `Prompt ziehen`
- Button `Demo-Antwort`
- lokaler Seitenaufrufzaehler

### Bewusst nicht umgesetzt

- serverseitige globale Aufrufstatistik
- Speicherung von Promptdaten
- Speicherung von Antwortdaten
- Speicherung von Mappingdaten
- automatische LLM-Integration in der oeffentlichen statischen Webapp

## Tests

Neue Testdateien:

- `datonym-gateway/tests/conftest.py`
- `datonym-gateway/tests/test_app.py`
- `datonym-gateway/tests/test_german_recognizers.py`
- `datonym-gateway/tests/test_service.py`
- `datonym-gateway/tests/test_tokens.py`

Getestet wird:

- Healthcheck
- `/v1/anonymize`
- `/v1/chat/completions` mit Mock-LLM
- keine Originalwerte in produktiver Anonymize-Antwort
- Demo-Endpoint mit sichtbarem Mapping
- Token-Wiederverwendung
- Token-Kollisionen
- unbekannte Tokens
- deutsche Recognizer-Beispiele
- zentrale globale Entities
- Gateway-Rueckpersonalisierung

Regelmaessiger Testlauf:

```powershell
.\.venv\Scripts\python.exe -m pytest datonym-gateway/tests -q
```

Letzter bekannter Stand:

```text
35 passed, 1 warning
```

Die Warnung stammt aus `fastapi.testclient` / Starlette und betrifft die
Testclient-Abhaengigkeit, nicht die DatOnym-Funktion.

## Lokale Ausfuehrung

### Gateway starten

```powershell
.\.venv\Scripts\python.exe -m uvicorn datonym_gateway.app:app --app-dir .\datonym-gateway --host 127.0.0.1 --port 8080
```

Lokale Gateway-Demo:

```text
http://127.0.0.1:8080/demo
```

### Statische Webapp lokal starten

```powershell
.\.venv\Scripts\python.exe -m http.server 8081 -d webapp --bind 127.0.0.1
```

Lokale Webapp:

```text
http://127.0.0.1:8081/
```

## GitHub Pages Deployment

Die statische Webapp wird auf `gh-pages` deployed. Der Branch enthaelt nur die
Dateien aus `webapp/`, damit die URL direkt die DatOnym-Testwebapp zeigt.

Aktive Pages-Konfiguration:

- Branch: `gh-pages`
- Pfad: `/`
- URL: `https://thomas-lauer.github.io/DatOnym/`

## Datei-Inventar der DatOnym-Ergaenzungen

### Presidio-Konfiguration

- `presidio-analyzer/presidio_analyzer/conf/datonym_de_analyzer.yaml`

### Gateway

- `datonym-gateway/.env.example`
- `datonym-gateway/README.md`
- `datonym-gateway/pyproject.toml`
- `datonym-gateway/datonym_gateway/__init__.py`
- `datonym-gateway/datonym_gateway/app.py`
- `datonym-gateway/datonym_gateway/config.py`
- `datonym-gateway/datonym_gateway/models.py`
- `datonym-gateway/datonym_gateway/operators.py`
- `datonym-gateway/datonym_gateway/presidio.py`
- `datonym-gateway/datonym_gateway/service.py`
- `datonym-gateway/datonym_gateway/tokens.py`

### Gateway-Demo

- `datonym-gateway/datonym_gateway/static/index.html`
- `datonym-gateway/datonym_gateway/static/styles.css`
- `datonym-gateway/datonym_gateway/static/app.js`

### Tests

- `datonym-gateway/tests/conftest.py`
- `datonym-gateway/tests/test_app.py`
- `datonym-gateway/tests/test_german_recognizers.py`
- `datonym-gateway/tests/test_service.py`
- `datonym-gateway/tests/test_tokens.py`

### Oeffentliche Webapp

- `webapp/.nojekyll`
- `webapp/README.md`
- `webapp/index.html`
- `webapp/styles.css`
- `webapp/app.js`

### Dokumentation

- `docs/datonym-aenderungen.md`

## Grenzen des aktuellen Stands

### Gateway

- MVP unterstuetzt nur textbasierte Chatnachrichten.
- Kein Streaming.
- Keine Tool Calls.
- Keine Bilder.
- Keine Datei-Uploads.
- Keine dauerhafte Mapping-Persistenz.

### Oeffentliche Webapp

- Die Browser-Erkennung ist ein leichtgewichtiges Testwerkzeug und kein Ersatz
  fuer Presidio mit spaCy.
- JavaScript-Recognizer koennen false positives und false negatives erzeugen.
- Die Webapp sendet nicht selbst an ein LLM.
- Die Rueckpersonalisierung funktioniert nur fuer Tokens, die in der aktuellen
  Browser-Sitzung erzeugt wurden.

## Zusammenfassung der wichtigsten Unterschiede

| Bereich | Original Presidio | DatOnym-Erweiterung |
| --- | --- | --- |
| Sprache | Schwerpunkt Englisch, deutsche Recognizer vorhanden | deutsches Analyzer-Profil mit `de_core_news_md` |
| Nutzung | Analyzer/Anonymizer als Bibliotheken und Services | Prompt-Gateway fuer LLM-Workflows |
| Tokenformat | Presidio-Operatoren frei konfigurierbar | stabile Tokens `#DATONYM_<ENTITY>_<0001>#` |
| Reversibilitaet | moeglich ueber Anonymizer/Deanonymizer | request-lokales Mapping und Rueckpersonalisierung |
| Persistenz | projektabhaengig | keine Mapping-Persistenz im MVP |
| UI | Presidio-Demos/Dokus | DatOnym Testwebapp und lokale Demo |
| LLM-Flow | nicht als zentrales Gateway im Core | OpenAI-kompatibles `/v1/chat/completions` Gateway |
| Oeffentliche Demo | nicht vorhanden | GitHub Pages Webapp |
