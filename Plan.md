# Plan

Stand: 24.09.2026 · veröffentlicht: 0.12.0, in Arbeit: 0.12.1 · API v1.5

Dieses Dokument hält **Reihenfolge, Stand und Entscheidungen** fest. Was die API liefert, steht in [`docs/API.md`](docs/API.md) — dort nachsehen, bevor ein Punkt umgesetzt wird (siehe `AGENTS.md`). Erledigtes abhaken und die Version dazuschreiben.

| # | Vorhaben | Stand | Release |
| --- | --- | --- | --- |
| 1 | Niederschlag und Prognose-Sensoren korrigieren | veröffentlicht | 0.7.0 |
| 2 | Kleines Paket: `days[].gust`, `temp_source`, `station_today` | veröffentlicht | 0.8.0 |
| 3 | DWD-Warnungen (`alerts`) | verworfen — dafür gibt es die DWD-Integration | – |
| 4 | Stündliche Vorhersage (`hours`) | veröffentlicht | 0.9.0 |
| 5 | Niederschlagsbilanz (`rain`) | verworfen — HA rechnet das selbst | – |
| 6 | Entity-IDs nach den Einstellungen des Nutzers | veröffentlicht | 0.10.0 |
| 7 | Diagnose-Download | veröffentlicht | 0.11.0 |
| 8 | Irreführende englische Namen | veröffentlicht | 0.12.0 |
| 9 | Zeitstempel `time` in `hours` nutzen | verworfen — Rückrechnung bestätigt und ausreichend | – |
| 10 | Fehler aus der Code-Durchsicht | umgesetzt | 0.12.1 |
| 11 | Tests im Repo | geplant | – |
| – | ETag / `If-None-Match` | verworfen | – |

## 1. Niederschlag und Prognose-Sensoren korrigieren

**Befund:** Laut API-Doku ist `current.rain` die *gemessene* Tagessumme, `rain_today` eine *Prognose*. Die Integration hat beides vertauscht behandelt. `tmax_today` und `tmin_today` sind ebenfalls Prognosen, nicht Tagesaggregate.

**Belege:**
- Verlauf 05.09.2026: `rain` steigt in 0,2-mm-Schritten auf 3,4 mm und fällt um Mitternacht auf 0; `rain_today` springt 1,5 → 6,3 → 3,1 → 0,1 → 0. Am 07.09. zeigte `rain_today` 0,2 mm ohne Regen.
- Die `rain`-Sektion meldet für September 3,4 mm — genau die Messung vom 05.09.
- Langzeitstatistik von `rain_today` für den 05.09.: 9,5 mm (jeder Rückgang als Zählerreset gewertet).
- Antwort vom 11.09., 23:00: `today.temp` enthält nur noch 22 und 23 Uhr; deren Max/Min ergeben exakt `tmax_today` 13,5 und `tmin_today` 12,4. Gemessen waren 24,4 °C, `days[0]` sagte 24 °C voraus. Die `*_today`-Werte gelten also nur für die **verbleibenden** Stunden.

**Umsetzung:**
- [x] `rain` → `total_increasing`
- [x] `rain_today`, `tmax_today`, `tmin_today` → keine State-Class
- [x] Deutsche Namen: „Station heute Niederschlag", „Prognose Resttag Niederschlag/Tmax/Tmin"
- [x] README (Tabelle, Erklärung, Upgrade-Hinweis, Beispiel), Beispiel-Dashboard, `docs/API.md`, `AGENTS.md`, CHANGELOG
- [x] Release 0.7.0 (11.09.2026)
- [x] Alte Statistik der drei Prognose-Sensoren gelöscht (12.09.2026, `recorder/clear_statistics`); die Meldungen „state class removed" verschwinden erst nach `recorder/update_statistics_issues` oder dem nächsten Prüflauf
- [x] Beim API-Betreiber bestätigen lassen, dass die `*_today`-Werte nur die restlichen Stunden abdecken. **Bestätigt am 17.09.2026**: Die Werte sind Min/Max bzw. Summe über das Stundenarray des Tages, in dem vergangene Stunden auf `null` stehen und vor der Rechnung herausfallen — übrig bleiben die verbleibenden Prognosestunden. Der Betreiber bestätigt ausdrücklich, dass sie auf die Vorhersage-Seite gehören und nicht in die Langzeitstatistik, und schärft seine Doku nach. Details in [`docs/API.md`](docs/API.md).

**Entscheidungen:**
- *Keine* State-Class statt `measurement` — die HA-Entwicklerdoku schließt „a prediction of the future" ausdrücklich aus.
- Entity-IDs und englische Namen bleiben (siehe „Englische Namen" unten).
- 0.7.0 statt 0.6.3: sichtbare Änderung an Statistik und Anzeigenamen.
- In der eigenen Instanz nutzt keine Automation, kein Skript und kein Dashboard die betroffenen Sensoren (geprüft 11.09.2026).

## 2. Kleines Paket

Alles aus bereits angeforderten Sektionen, kein zusätzlicher Abruf. Formate an der Antwort vom 11.09.2026 bestätigt.

- [x] `days[].gust` → `native_wind_gust_speed` in der Tagesvorhersage. Die aktuelle Böe bleibt bewusst leer (`gust_max` ist das Tagesmaximum).
- [x] `current.temp_source` (`live` / `forecast`) → Attribut `source` am Sensor Außentemperatur
- [x] `station_today.wind_max` → neuer Sensor „Station heute Wind max" / „Station max wind today" → `sensor.kraichtal_wetter_station_max_wind_today`. State-Class wie die übrigen Station-Sensoren (`measurement`, Begründung in CHANGELOG 0.5.5).
- [x] `station_today.tmax_time`, `tmin_time`, `gust_time` → Attribut `time` an den jeweiligen Station-Sensoren (`"HH:MM"`, unverändert durchgereicht)
- [x] `station_today.gust_bft` → Attribut `beaufort` am Sensor „Station heute Böe"
- [x] Attribute über `attributes` in `KraichtalWetterSensorEntityDescription`, Übersetzungen unter `state_attributes`
- [x] Getestet gegen HA 2026.9.2 mit der Antwort vom 11.09.2026 (24 Prüfungen, Randfälle `null`/fehlend) und mit Hassfest lokal
- [x] Release 0.8.0 (11.09.2026)
- [x] In einer echten Instanz bestätigt (12.09.2026): Sensor liegt als `sensor.garten_kraichtal_wetter_station_heute_wind_max` an, die Attribute kommen an (`time: "15:22"`, `beaufort: 4`)

## 3. DWD-Warnungen (`alerts`) — verworfen (12.09.2026)

Dafür gibt es die mitgelieferte Integration **„Deutscher Wetterdienst (DWD) Weather Warnings"** (`dwd_weather_warnings`), und sie ist der API in jedem Punkt überlegen, der zählt:

| | `alerts` dieser API | DWD-Integration |
| --- | --- | --- |
| Quelle | DWD über den API-Betreiber | DWD direkt (WFS-API) |
| Gültigkeit | Fließtext | `start_time` / `end_time` als Zeitstempel |
| Verhaltenshinweise | – | `instruction` |
| Vorwarnung | nur Flag `active` | eigener Sensor „Vorwarnstufe" |
| Weitere Felder | `sev`, `level`, `color` | `event_code`, `level`, `parameters`, `color`, `headline`, `description` |
| Ort | fest die Station | wählbare Warnzelle, auch per Gerätestandort |
| Takt | unser Abrufintervall | 15 Minuten |

Übrig blieben als Vorteile nur der fertige deutsche Text „Warnstufe 3 – Schwer" und die Farbe. Das wiegt eine zweite, schwächere Warnquelle nicht auf.

Der Sensor „Warnungen" aus `current.warnings` bleibt als schnelle Anzahl erhalten; die README verweist für Details auf die DWD-Integration.

## 4. Stündliche Vorhersage (`hours`)

12 Einträge mit `label`, `temp`, `pop`, `wind`, `icon` — keine Regenmenge, keine Windrichtung.

- [x] `hours` in `REQUESTED_SECTIONS`, `WeatherEntityFeature.FORECAST_HOURLY`, `async_forecast_hourly()` mit eigenem Cache
- [x] Zeitstempel: verankert an der ersten beschrifteten Stunde (statt an `meta.generated`, sonst müsste man raten, ob die API „Jetzt" auf- oder abrundet), von dort in **UTC** weitergezählt; widerspricht eine Beschriftung dem Schritt, gilt die Beschriftung
- [x] Zeitzone fest `Europe/Berlin` (`API_TIME_ZONE`), auch für den Kalendertag der Tagesvorhersage
- [x] Nebenbefund behoben: Die Entität benachrichtigt jetzt ihre Forecast-Abonnenten (`async_update_listeners`) — vorher blieb die Vorhersage in einem offenen Dashboard stehen
- [x] Getestet gegen beide Zeitumstellungen, Mitternacht, Lücken und fehlende Beschriftungen
- [x] Release 0.9.0 (12.09.2026)
- [x] In einer echten Instanz bestätigt (12.09.2026, 15:2x Uhr): zwölf Einträge ab 15:00, lückenlos stündlich über Mitternacht bis 02:00

**Erledigt — beantwortet am 17.09.2026.** Die API führt die Stundenwerte in 24 festen Slots pro Kalendertag; es gibt in der Nacht zum 25.10.2026 **genau ein** `"02:00"`, gefolgt von `"03:00"`. Zwei Instanzen der Quelle werden in denselben Slot gemittelt. Im März fehlt 02:00 ganz, auf `"01:00"` folgt `"03:00"`. Die Reihe ist in diesen beiden Nächten also nicht garantiert lückenlos — an allen anderen Tagen schon.

`_hourly_datetimes()` deckt das ab, ohne Änderung: Weil bei einem Widerspruch die Beschriftung gilt, entsteht im Oktober 02:00 MESZ gefolgt von 03:00 MEZ (real zwei Stunden Abstand, genau der Sprung in den Daten), im März 01:00 MEZ gefolgt von 03:00 MESZ. Die Zeitstempel bleiben eindeutig und streng steigend. Nachgerechnet am 17.09.2026 mit beiden Label-Reihen — die Tabellen mit den konkreten Zeitstempeln stehen in [`docs/API.md`](docs/API.md) unter „Zeitumstellung: was die API tatsächlich tut". Die verbleibende Unschärfe — der eine 02:00-Eintrag wird auf den ersten Durchlauf gelegt, obwohl er gemittelt sein kann — steht in [`docs/API.md`](docs/API.md) und ist bewusst in Kauf genommen.

**Eine Messung in der Umstellungsnacht ist damit nicht mehr nötig.** Wer sie trotzdem fahren will: Umgestellt wird um 03:00 MESZ auf 02:00 MEZ. Doppelt durchlaufen wird die Stunde **02:00–02:59**, *nicht* 02:xx und 03:xx — lokal 03:20 gibt es nur einmal. Die drei sinnvollen Abrufe in UTC:

| Lauf | Lokal | UTC | Was er zeigt |
| --- | --- | --- | --- |
| 1 | 02:20 MESZ | `2026-10-25T00:20:00Z` | erster Durchlauf der doppelten Stunde |
| 2 | 02:20 MEZ | `2026-10-25T01:20:00Z` | zweiter Durchlauf — der entscheidende |
| 3 | 03:20 MEZ | `2026-10-25T02:20:00Z` | Kontrolle, Reihe wieder normal |

Seit 0.11.0 genügt dafür ein Diagnose-Abruf, der die rohe Antwort mitliefert — kein `curl` mit Schlüssel nötig:
`ha_get_integration(entry_id="01M20W183QPDMPPKYSNFT8N23N", include_diagnostics=True)`, die `hours` liegen unter `data.data.api.hours`. Alternativ das `curl`-Rezept unter „Testdaten beschaffen".

## 5. Niederschlagsbilanz (`rain`) — verworfen (12.09.2026)

Seit 0.7.0 trägt der gemessene Niederschlag `total_increasing`, also bildet Home Assistant Monats- und Jahressummen selbst — aus den eigenen Daten und für jeden beliebigen Zeitraum. Eigenständig blieben nur der Vergleich mit dem Klimamittel (`expected`, `annual_avg`, `delta`), die Jahressumme aus der Zeit vor der Installation und `station.h24`.

Das wiegt den Preis nicht auf: Die Sektion darf laut Fair use nur ein- bis zweimal täglich abgerufen werden, bräuchte also einen zweiten Coordinator mit eigenem Intervall — deutlich mehr bewegliche Teile als der Nutzen rechtfertigt. Wer die Klimazahlen sehen will, findet sie im Dashboard der Quelle.

## 6. Entity-IDs: alte Migration gegen HA-Schema — zu entscheiden

**Befund (12.09.2026, am HA-Quellcode 2026.9 geprüft):** Home Assistant bildet Entity-IDs aus dem Namen in der Sprache der Instanz, sofern sie in `NATIVE_ENTITY_IDS` steht — `de` steht dort — und stellt Bereich und Gerät voran (`EntityNamePart.AREA, DEVICE, ENTITY`). Die bisherige Annahme in `AGENTS.md`, IDs entstünden sprachunabhängig aus `en.json`, war falsch.

Sichtbar geworden am neuen Sensor aus 0.8.0: Er heißt in einer deutschen Instanz mit Bereich `sensor.garten_kraichtal_wetter_station_heute_wind_max` — deutscher Name, Bereich davor. Die älteren Sensoren tragen nur deshalb englische IDs, weil `_SENSOR_ENTITY_ID_MIGRATION` sie 0.5.0 dorthin umbenannt hat.

**Das Problem:** Die Migration läuft bei *jedem* Setup und benennt alles um, was noch die alten deutschen Object-IDs trägt. Auf einer Neuinstallation ohne Bereich legt HA heute genau solche deutschen IDs an — beim nächsten Start zieht die Migration sie nach Englisch. Mit Bereich greift sie nicht, weil das Präfix nicht passt. Ergebnis: Neuinstallationen bekommen je nach Bereich unterschiedliche, teils gemischte IDs.

**Entscheidung (12.09.2026): deutsche IDs, und zwar in dem Format, das der Nutzer eingestellt hat.** Seit HA 2026.8 lässt sich festlegen, aus welchen Teilen eine Entity-ID besteht (Bereich, Etage, Gerät, Entität). Statt Ziel-IDs fest zu verdrahten, fragen wir HA über `registry.async_regenerate_entity_id()`, wie es die Entität heute benennen würde — das trifft Sprache und Format automatisch.

- [x] Feste Ziel-IDs raus; `_LEGACY_SENSOR_OBJECT_IDS` listet nur noch die Alt-IDs (englisch aus 0.5.0, deutsch von davor), die überhaupt angefasst werden dürfen
- [x] Einmalig über `async_migrate_entry` und die Config-Entry-Version (`VERSION = 2`); die Umbenennung selbst am Ende von `async_setup_entry`, weil die Registry erst dann die aktuellen Namen kennt
- [x] `async_regenerate_entity_id()` gibt es seit HA 2026.3, das einstellbare Format seit 2026.8 — passt zum Minimum 2026.3, ältere Versionen bekommen eben das damalige Standardformat
- [x] README (Tabelle, Beispiele, Upgrade-Hinweis), Beispiel-Dashboard, `AGENTS.md`
- [x] Getestet: Umbenennung aus beiden Alt-Zuständen, Format mit Bereich, selbst vergebene IDs, bereits korrekte IDs, englischsprachige Instanz, Einmaligkeit und die Reihenfolge im Setup
- [x] Release 0.10.0 (12.09.2026)
- [x] Verweise in der Testinstanz nachgezogen (12.09.2026): eine Automation und sieben Stellen in zwei Dashboards; Helfer und Gruppen waren nicht betroffen

**Folge für Bestandsinstallationen mit Bereich:** Die Entitäten bekommen das Bereichspräfix, das eine Neuinstallation auch hätte — aus `sensor.kraichtal_wetter_outdoor_temperature` wird dort `sensor.garten_kraichtal_wetter_aussentemperatur`. Genau das macht sie zu den bereits nativ angelegten Sensoren konsistent.

## 7. Diagnose-Download

**Warum:** Das README bittet um Fehlerberichte, aber die Antwort der API — das, was einen Fehler überhaupt erklärt — bekam man nur, indem man sie von Hand mit dem eigenen Schlüssel abfragte. Die HA-Standardplattform `diagnostics` schließt die Lücke, ohne eine Entität oder einen Abruf hinzuzufügen.

**Umsetzung:**
- [x] `diagnostics.py` mit `async_get_config_entry_diagnostics`: Config-Entry, angefragte Sektionen, Coordinator-Zustand und die letzte API-Antwort
- [x] Redaktion auf drei Ebenen: `async_redact_data` über die Feldnamen `key`/`api_key`/`apikey`, danach ein Durchlauf über die *Werte* (dort steckt er bei einem Eintrag von vor 0.4.4, in der gespeicherten URL), und derselbe Filter über den Text von `coordinator.last_exception`
- [x] Die URL läuft durch `_split_api_key()` aus `coordinator.py` — dieselbe Funktion, die auch den Client schützt, statt einer zweiten Kopie der Logik
- [x] 29 Prüfungen gegen HA 2026.9.2 (siehe „Ohne laufende Instanz prüfen"), darunter der Fall, in dem der Schlüssel **nur** in der URL steht und `async_redact_data` ihn nicht sehen kann
- [x] README-Abschnitt „Ein Problem melden", CHANGELOG, `AGENTS.md`
- [x] In einer echten Instanz bestätigt (17.09.2026, 0.11.0): `key` steht auf `**REDACTED**`, `api_url` und `request.url` sind sauber, `key_in_url` false, `coordinator.last_update_success` true, die vollständige Antwort (`meta`, `current`, `days`, `hours`) liegt bei. Kein Schlüssel im Dump.
- **Merke:** Home Assistant verpackt die Ausgabe der Integration noch einmal — im Download liegt sie unter `data`, neben den von HA ergänzten Blöcken `home_assistant`, `custom_components`, `integration_manifest`, `setup_times` und `issues`. Wer im Dump nach `entry` oder `coordinator` sucht, muss also eine Ebene tiefer.
- **Mit im Dump:** `meta.lat`/`meta.lon` der Station (49.13/8.73). Das ist der öffentliche Standort der Wetterstation, nicht der des Nutzers — unbedenklich für ein Issue.

**Entscheidung:** `system_health.py` wurde miterwogen und zurückgestellt — es überschneidet sich mit dem vorhandenen Diagnose-Sensor „API-Status" und beantwortet nur, *ob* etwas klemmt, nicht *was*.

## 8. Irreführende englische Namen

**Befund:** Was 0.7.0 auf der deutschen Seite geradegezogen hat, blieb auf der englischen stehen. Dort hieß eine Prognose weiter „Precipitation today", als wäre sie ein Messwert, und der gemessene Niederschlag schlicht „Precipitation" — ohne den Hinweis, dass er von der Station kommt.

| Schlüssel | bisher | jetzt | deutsches Vorbild |
| --- | --- | --- | --- |
| `rain` | Precipitation | Station precipitation today | Station heute Niederschlag |
| `tmax_today` | Max temperature today | Forecast rest of day max temperature | Prognose Resttag Tmax |
| `tmin_today` | Min temperature today | Forecast rest of day min temperature | Prognose Resttag Tmin |
| `rain_today` | Precipitation today | Forecast rest of day precipitation | Prognose Resttag Niederschlag |

**Umsetzung:**
- [x] `strings.json` und `translations/en.json` identisch geändert — die beiden sind byte-gleich, sonst scheitert Hassfest (vgl. 0.5.7)
- [x] Die sechs `station_today_*`-Schlüssel blieben unangetastet, sie hießen bereits „Station … today"
- [x] README-Upgrade-Hinweis, CHANGELOG, Release 0.12.0

**Entscheidung: keine zweite Entity-ID-Migration.** Bestehende englische Installationen behalten ihre IDs, nur der Anzeigename ändert sich. Eine erzwungene Umbenennung kostet mehr, als ein klarerer Name einbringt — Home Assistant schreibt Verweise in eigenen Dashboards und Automationen nicht mit um, das war die Lehre aus Punkt 6. Die Folge ist bewusst in Kauf genommen: Eine englische Neuinstallation bekommt IDs nach dem neuen Namen, eine bestehende behält die alten.

**Nebenbefund:** `.ruff.toml` im Wurzelverzeichnis hält fest, dass `homeassistant` als First-Party sortiert wird. Ohne die Datei meldet ruff I001 für `config_flow.py` und `coordinator.py` und will die Leerzeile vor dem `homeassistant`-Block entfernen — das wäre falsch, die übrigen vier Module trennen ihn ebenso ab wie der HA-Core selbst. Der Code blieb unverändert.

## 9. Zeitstempel `time` in `hours` nutzen — verworfen (24.09.2026)

Der Betreiber hat am 17.09.2026 auf unsere Anregung hin zugesagt, neben `label` in jedem `hours`-Eintrag ein Feld `time` mitzuliefern (ISO 8601 mit Offset, z. B. `"2026-10-25T02:00:00+02:00"`). Am 24.09.2026 war es noch nicht live.

**Warum wir es nicht brauchen:** Angeregt hatten wir es, solange unklar war, wie die API die Zeitumstellung beschriftet. Seit der Antwort vom 17.09.2026 ist das geklärt, und `_hourly_datetimes()` verkraftet beide Umstellungsnächte nachweislich (Punkt 4). `time` würde das Ergebnis nur in diesen zwei Nächten berühren, und selbst dort bleibt die Slot-Struktur: ein einziger gemittelter 02:00-Eintrag im Oktober, keiner im März. Der Gewinn — eine Stunde Unschärfe an einem Eintrag, einmal im Jahr — trägt keinen zweiten Codepfad samt Rückfallebene.

**Auch `current.obs_time` ersetzt es nicht:** Das ist die Uhrzeit der letzten Stationsmessung (`"07:50"`, nur `HH:MM`, Datum getrennt in `obs_date`, kein Offset). Es beschreibt die Messung, nicht die zwölf Vorhersagestunden. Den Tagesanker liefert bereits `meta.generated` mit Datum und Offset.

**Folge:** Taucht `time` in der Antwort auf, wird es wie jedes andere ungenutzte Feld ignoriert. Beim Betreiber ist nichts zurückzunehmen.

## 10. Fehler aus der Code-Durchsicht (24.09.2026)

- [x] Options-Flow als `OptionsFlowWithReload` — ein neues Intervall galt erst nach einem Neustart
- [x] Intervall aus der Einrichtung (`entry.data`) wird gelesen — bisher nur `entry.options`, jede Installation lief mit 300 s
- [x] API-Key in Einrichtung und Reauth gegen die API prüfen (`invalid_auth`, `cannot_connect`, `unknown`); Reauth auf `_get_reauth_entry()` / `async_update_reload_and_abort()`
- [x] Abruffehler im Client nur noch auf `debug` — der Coordinator meldet Ausfall und Erholung selbst
- [x] `ContentTypeError` als „API returned no JSON" statt „HTTP error 200"
- [x] README: falsches Versprechen „Key jederzeit unter Konfiguration ändern" korrigiert
- [x] 26 Prüfungen gegen HA 2026.9.3, Gegenprobe mit 0.12.0
- [ ] Release 0.12.1

**Idee, nicht umgesetzt:** Ein Reconfigure-Schritt, mit dem man den Key auch ohne Ablehnung durch die API tauschen kann. Das README hat ihn versprochen, gebraucht hat ihn bisher niemand. `_async_validate_key()` wäre wiederverwendbar.

**Zurückgestellt:** `hass.data` → `entry.runtime_data`. Moderner, aber berührt alle Plattformen und die Diagnose, ohne dass Nutzer etwas davon merken — passt besser zu Punkt 11, wenn Tests es absichern.

## 11. Tests im Repo — geplant

Die Prüfungen bisher liefen ad hoc in einer lokalen venv und sind nicht eingecheckt. Ziel: `tests/` mit `pytest-homeassistant-custom-component` und ein CI-Job. Zuerst die heiklen Stellen: Zeitumstellung in `_hourly_datetimes()`, Redaktion in `diagnostics.py`, Migration der Entity-IDs, Key-Prüfung und Intervall aus 0.12.1.

**Merke für die Einrichtung:** Das Paket bringt ein eigenes `custom_components` mit (`testing_config`), das unseres verdeckt. In der `conftest.py` den Repo-Pfad an `custom_components.__path__` anhängen, dazu die Fixture `enable_custom_integrations` autouse. `MockConfigEntry.start_reauth_flow()` gibt es, am echten `ConfigEntry` heißt es `async_start_reauth()`.

## Verworfen

- **Feld `time` in `hours`:** siehe Punkt 9 — die Rückrechnung ist bestätigt und reicht.
- **ETag / `If-None-Match`:** Bei unserem Takt kommt ein 304 praktisch nie vor (Station alle paar Minuten, Server-Cache 5 Minuten, Abruf frühestens alle 5 Minuten). Kein Gewinn für zusätzliche Fehlerpfade.
- **`alerts`:** siehe Punkt 3 — die DWD-Integration kann es besser.
- **`rain`:** siehe Punkt 5 — Home Assistant rechnet die Summen selbst.
- **`today`, `trend`, `models`, `astro`, `climate`:** Begründung in `docs/API.md`.

## Entschieden, nicht noch einmal aufrollen

- **Die drei „Prognose Resttag"-Sensoren bleiben standardmäßig aktiv** (12.09.2026). Sie standardmäßig zu deaktivieren wurde erwogen und verworfen: Sie beantworten „wie warm wird es heute noch" und „wie viel Regen kommt heute noch" als *einzelnen Zustand*, und das kann sonst nichts. Die Tagesvorhersage gilt für den ganzen Kalendertag, die Stundenvorhersage liefert nur eine Liste, aus der man das Maximum erst per Template ziehen müsste. Für eine Bedingung — Bewässerung ist der typische Fall — ist der Sensor der einfache Weg.
- Dass sie **keine Langzeitstatistik** führen, ist kein Mangel, sondern die Vorgabe von Home Assistant für Vorhersagen. Home Assistant meldet nach dem Update einmalig „state class removed"; die alten Daten gehören gelöscht (`recorder/clear_statistics`, danach `recorder/update_statistics_issues`).

## Übergreifend

- ~~**Englische Namen.**~~ Erledigt in 0.12.0, siehe Punkt 8.
- **Fair use.** Die Doku empfiehlt für `days` und `hours` 15–30 Minuten, wir fragen alle 5 Minuten ab. Wegen des 5-Minuten-Server-Caches vertretbar. Kommt `rain` (Punkt 5), braucht es ohnehin einen zweiten Abruf — dann prüfen, ob `days`/`hours`/`alerts` mit umziehen.
- ~~**Zeitzone.**~~ Erledigt in 0.9.0: Der Kalendertag kommt aus `Europe/Berlin`, die Anzeige bleibt auf lokaler Mitternacht, damit die Karte den erwarteten Wochentag beschriftet.
- **Bereich in der Entity-ID.** Home Assistant stellt Bereich und Gerät voran, siehe Punkt 6.

## Außerhalb des Codes

- [ ] **HACS-Standardkatalog:** [hacs/default#10787](https://github.com/hacs/default/pull/10787) ist offen, kein Entwurf, alle Checks grün, `mergeable`. Der PR zeigt `CHANGES_REQUESTED` — das ist die automatische Prüfung des hacs-bot vom 09.09.2026 wegen „HACS" im damaligen Repo-Namen `kraichtal-wetter-hacs`. Längst erledigt: Das Repo heißt `t0bn1k/ha-kraichtal-wetter`, der PR wurde elf Minuten nach der Prüfung auf den neuen Namen umgestellt. Der Status bleibt stehen, bis ein Maintainer ihn verwirft; eine menschliche Rückfrage gibt es nicht (geprüft 24.09.2026). Davor stehen 904 ältere offene Nicht-Draft-PRs (17.09.2026) — genau die Sortierung, auf die der hacs-bot verlinkt. Die Position bewegt sich kaum, weil etwa so viele PRs nachkommen wie gemergt werden (203 Merges in 30 Tagen). Streng der Reihe nach wird aber nicht gearbeitet: zuletzt gemergte Katalog-PRs lagen 5–11 Wochen zwischen Erstellung und Merge, die 904 sind also Obergrenze, nicht Wartezeit. Nicht kommentieren — der Bot bittet ausdrücklich darum.
- [ ] **Nach dem Merge:** Installationsanleitung vom benutzerdefinierten Repository auf die Katalogsuche umstellen und den HACS-Badge von „Custom" auf „Default" ziehen. Sterne- und Installations-Badge stehen seit 17.09.2026 im README (`AGENTS.md`); der Installations-Badge füllt sich von selbst, sobald `kraichtal_wetter` in den HA-Analytics auftaucht.
- **Icon in HACS:** fehlt, ist bekannt und nicht am Repo zu lösen (`AGENTS.md`).
- [x] **Anfrage an den API-Betreiber** (gestellt und beantwortet am 17.09.2026). Zwei Fragen in einem Schreiben, das bewusst **nicht** im Repo liegt — es ist ein Brief, kein Projektdokument. Beide Antworten stehen in [`docs/API.md`](docs/API.md), beide offenen Punkte sind damit erledigt:
  1. **Beschriftung der wiederholten Stunde:** ein einziges `"02:00"`, kein doppeltes — 24 feste Slots pro Kalendertag, zwei Instanzen werden gemittelt (Punkt 4). Die Anregung, je Eintrag einen eindeutigen Zeitpunkt mitzuliefern, hat der Betreiber als Feld `time` angenommen; wir nutzen es nicht (Punkt 9).
  2. **`*_today` gilt nur für die restlichen Stunden:** bestätigt, samt Mechanismus (Punkt 1). Der Betreiber schärft die Beschreibung in seiner Doku nach.

## Testdaten beschaffen

Eine echte Antwort, der Key steht nur im Header und landet nicht in der Datei:

```sh
curl -s -H "X-API-Key: DEIN_KEY" "https://kraichtal-wetter.de/dashboard/api.php?section=current,days,hours,alerts,rain&pretty=1" > /tmp/kw.json
```

Eine Antwort aus der Nacht der Zeitumstellung (25.10.2026, 02:00–03:00) wird **nicht mehr gebraucht** — die Beschriftungen sind seit dem 17.09.2026 vom Betreiber beschrieben (Punkt 4).

## Ohne laufende Instanz prüfen

So wurde Punkt 2 getestet — für 3 und 4 wiederverwendbar:

- **Home Assistant als Paket:** `python3 -m venv havenv && havenv/bin/pip install homeassistant` (braucht Python ≥ 3.14.2). Damit lassen sich Sensor- und Wetter-Entität direkt instanziieren und mit einer gespeicherten API-Antwort füttern — ohne `hass`-Instanz, der Coordinator ist ein einfaches Objekt mit `data`.
- **Hassfest lokal:** `script/` aus `home-assistant/core` (Sparse-Checkout, Tag passend zur installierten Version), dazu `pip install infrared-protocols tqdm ruff`, dann `python -m script.hassfest --integration-path custom_components/kraichtal_wetter`. Fängt vor allem Übersetzungsfehler ab, bevor die CI nach dem Taggen daran scheitert (vgl. 0.5.7).
