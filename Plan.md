# Plan

Stand: 12.09.2026 · veröffentlicht: 0.10.0 · API v1.5

Dieses Dokument hält **Reihenfolge, Stand und Entscheidungen** fest. Was die API liefert, steht in [`docs/API.md`](docs/API.md) — dort nachsehen, bevor ein Punkt umgesetzt wird (siehe `AGENTS.md`). Erledigtes abhaken und die Version dazuschreiben.

| # | Vorhaben | Stand | Release |
| --- | --- | --- | --- |
| 1 | Niederschlag und Prognose-Sensoren korrigieren | veröffentlicht | 0.7.0 |
| 2 | Kleines Paket: `days[].gust`, `temp_source`, `station_today` | veröffentlicht | 0.8.0 |
| 3 | DWD-Warnungen (`alerts`) | verworfen — dafür gibt es die DWD-Integration | – |
| 4 | Stündliche Vorhersage (`hours`) | veröffentlicht | 0.9.0 |
| 5 | Niederschlagsbilanz (`rain`) | verworfen — HA rechnet das selbst | – |
| 6 | Entity-IDs nach den Einstellungen des Nutzers | veröffentlicht | 0.10.0 |
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
- [ ] Optional beim API-Autor bestätigen lassen, dass die `*_today`-Werte nur die restlichen Stunden abdecken (beobachtet, nicht dokumentiert)

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

**Offen:** Was die API um 02:00 am 25.10.2026 tatsächlich in die Beschriftungen schreibt, ist Annahme — der Code kommt mit beiden plausiblen Varianten zurecht. Bei Gelegenheit eine Antwort aus dieser Nacht sichern.

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

## Verworfen

- **ETag / `If-None-Match`:** Bei unserem Takt kommt ein 304 praktisch nie vor (Station alle paar Minuten, Server-Cache 5 Minuten, Abruf frühestens alle 5 Minuten). Kein Gewinn für zusätzliche Fehlerpfade.
- **`alerts`:** siehe Punkt 3 — die DWD-Integration kann es besser.
- **`rain`:** siehe Punkt 5 — Home Assistant rechnet die Summen selbst.
- **`today`, `trend`, `models`, `astro`, `climate`:** Begründung in `docs/API.md`.

## Entschieden, nicht noch einmal aufrollen

- **Die drei „Prognose Resttag"-Sensoren bleiben standardmäßig aktiv** (12.09.2026). Sie standardmäßig zu deaktivieren wurde erwogen und verworfen: Sie beantworten „wie warm wird es heute noch" und „wie viel Regen kommt heute noch" als *einzelnen Zustand*, und das kann sonst nichts. Die Tagesvorhersage gilt für den ganzen Kalendertag, die Stundenvorhersage liefert nur eine Liste, aus der man das Maximum erst per Template ziehen müsste. Für eine Bedingung — Bewässerung ist der typische Fall — ist der Sensor der einfache Weg.
- Dass sie **keine Langzeitstatistik** führen, ist kein Mangel, sondern die Vorgabe von Home Assistant für Vorhersagen. Home Assistant meldet nach dem Update einmalig „state class removed"; die alten Daten gehören gelöscht (`recorder/clear_statistics`, danach `recorder/update_statistics_issues`).

## Übergreifend

- **Englische Namen.** „Precipitation today", „Max temperature today" usw. sind für eine englischsprachige Oberfläche weiterhin irreführend — es sind Prognosen. Sie zu korrigieren betrifft nach Punkt 6 nur noch englischsprachige Neuinstallationen, ist also billig geworden. Offen, weil niemand danach gefragt hat.
- **Fair use.** Die Doku empfiehlt für `days` und `hours` 15–30 Minuten, wir fragen alle 5 Minuten ab. Wegen des 5-Minuten-Server-Caches vertretbar. Kommt `rain` (Punkt 5), braucht es ohnehin einen zweiten Abruf — dann prüfen, ob `days`/`hours`/`alerts` mit umziehen.
- ~~**Zeitzone.**~~ Erledigt in 0.9.0: Der Kalendertag kommt aus `Europe/Berlin`, die Anzeige bleibt auf lokaler Mitternacht, damit die Karte den erwarteten Wochentag beschriftet.
- **Bereich in der Entity-ID.** Home Assistant stellt Bereich und Gerät voran, siehe Punkt 6.

## Außerhalb des Codes

- [ ] **HACS-Standardkatalog:** [hacs/default#10787](https://github.com/hacs/default/pull/10787) ist offen, alle Checks grün, rund 900 PRs davor (11.09.2026). Nicht kommentieren — der Bot bittet ausdrücklich darum.
- [ ] **Nach dem Merge:** Downloads-Badge einbauen (Vorlage in `AGENTS.md`) und die Installationsanleitung vom benutzerdefinierten Repository auf die Katalogsuche umstellen.
- **Icon in HACS:** fehlt, ist bekannt und nicht am Repo zu lösen (`AGENTS.md`).

## Testdaten beschaffen

Eine echte Antwort, der Key steht nur im Header und landet nicht in der Datei:

```sh
curl -s -H "X-API-Key: DEIN_KEY" "https://kraichtal-wetter.de/dashboard/api.php?section=current,days,hours,alerts,rain&pretty=1" > /tmp/kw.json
```

Eine Antwort aus der Nacht der Zeitumstellung (25.10.2026, 02:00–03:00) wäre nützlich, um die Beschriftungen der Stundenwerte gegenzuprüfen.

## Ohne laufende Instanz prüfen

So wurde Punkt 2 getestet — für 3 und 4 wiederverwendbar:

- **Home Assistant als Paket:** `python3 -m venv havenv && havenv/bin/pip install homeassistant` (braucht Python ≥ 3.14.2). Damit lassen sich Sensor- und Wetter-Entität direkt instanziieren und mit einer gespeicherten API-Antwort füttern — ohne `hass`-Instanz, der Coordinator ist ein einfaches Objekt mit `data`.
- **Hassfest lokal:** `script/` aus `home-assistant/core` (Sparse-Checkout, Tag passend zur installierten Version), dazu `pip install infrared-protocols tqdm ruff`, dann `python -m script.hassfest --integration-path custom_components/kraichtal_wetter`. Fängt vor allem Übersetzungsfehler ab, bevor die CI nach dem Taggen daran scheitert (vgl. 0.5.7).
