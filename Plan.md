# Plan

Stand: 12.09.2026 · veröffentlicht: 0.9.0 · API v1.5

Dieses Dokument hält **Reihenfolge, Stand und Entscheidungen** fest. Was die API liefert, steht in [`docs/API.md`](docs/API.md) — dort nachsehen, bevor ein Punkt umgesetzt wird (siehe `AGENTS.md`). Erledigtes abhaken und die Version dazuschreiben.

| # | Vorhaben | Stand | Release |
| --- | --- | --- | --- |
| 1 | Niederschlag und Prognose-Sensoren korrigieren | veröffentlicht | 0.7.0 |
| 2 | Kleines Paket: `days[].gust`, `temp_source`, `station_today` | veröffentlicht | 0.8.0 |
| 3 | DWD-Warnungen (`alerts`) | verworfen — dafür gibt es die DWD-Integration | – |
| 4 | Stündliche Vorhersage (`hours`) | veröffentlicht | 0.9.0 |
| 5 | Niederschlagsbilanz (`rain`) | neu bewerten | – |
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
- [ ] Nach dem Update in der eigenen Instanz: *Entwicklerwerkzeuge → Statistik* — die Hinweise zu den drei Prognose-Sensoren bestätigen und die alten Daten löschen
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
- [ ] Nach dem Update in der eigenen Instanz prüfen: Entity-ID des neuen Sensors (evtl. mit Bereichspräfix, siehe unten), Attribute in der Oberfläche übersetzt

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
- [ ] Nach dem Update prüfen: Vorhersagekarte mit `forecast_type: hourly`

**Offen:** Was die API um 02:00 am 25.10.2026 tatsächlich in die Beschriftungen schreibt, ist Annahme — der Code kommt mit beiden plausiblen Varianten zurecht. Bei Gelegenheit eine Antwort aus dieser Nacht sichern.

## 5. Niederschlagsbilanz (`rain`) — neu bewerten

Monats- und Jahressummen bildet Home Assistant nach 0.7.0 selbst aus `rain`. Eigenständig wären nur `expected`, `annual_avg`, `delta` („zu trocken um X mm"), die Jahressumme aus der Zeit vor der Installation und `station.h24` (nicht dokumentiert). Laut Fair use nur ein- bis zweimal täglich abzurufen — bräuchte einen zweiten, langsamen Abruf.

- [ ] Entscheiden, ob sich das lohnt. Wenn ja, eher nur `delta` und `year`.

## Verworfen

- **ETag / `If-None-Match`:** Bei unserem Takt kommt ein 304 praktisch nie vor (Station alle paar Minuten, Server-Cache 5 Minuten, Abruf frühestens alle 5 Minuten). Kein Gewinn für zusätzliche Fehlerpfade.
- **`alerts`:** siehe Punkt 3 — die DWD-Integration kann es besser.
- **`today`, `trend`, `models`, `astro`, `climate`:** Begründung in `docs/API.md`.

## Übergreifend

- **Englische Namen.** „Precipitation today", „Max temperature today" usw. sind für die englische Oberfläche weiterhin irreführend. Eine Änderung verschiebt aber die Entity-IDs *neuer* Installationen. Optionen: lassen · ändern und in der README beide IDs nennen · ändern mit Migration (bricht Automationen). Empfehlung: lassen, solange niemand danach fragt.
- **Fair use.** Die Doku empfiehlt für `days` und `hours` 15–30 Minuten, wir fragen alle 5 Minuten ab. Wegen des 5-Minuten-Server-Caches vertretbar. Kommt `rain` (Punkt 5), braucht es ohnehin einen zweiten Abruf — dann prüfen, ob `days`/`hours`/`alerts` mit umziehen.
- ~~**Zeitzone.**~~ Erledigt in 0.9.0: Der Kalendertag kommt aus `Europe/Berlin`, die Anzeige bleibt auf lokaler Mitternacht, damit die Karte den erwarteten Wochentag beschriftet.
- **Bereich in der Entity-ID.** In einer Instanz, deren Gerät einem Bereich zugeordnet ist, heißt der API-Status `sensor.garten_kraichtal_wetter_api_status` statt `sensor.kraichtal_wetter_api_status`. Vermutlich übernimmt Home Assistant den Bereich in die ID neu angelegter Entitäten. Die README kann nur den Normalfall zeigen; betrifft jeden neuen Sensor aus 2 und 3.

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
