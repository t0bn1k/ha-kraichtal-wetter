# Die Kraichtal-Wetter-API aus Sicht dieser Integration

Maßgeblich ist die offizielle Dokumentation: <https://kraichtal-wetter.de/dashboard/api-doku.html> (API v1.5).
Dieses Dokument hält fest, **was die Integration davon nutzt, was bewusst nicht, und was für später vorgemerkt ist** — damit eine neue Funktion nicht auf Vermutungen über die API gebaut wird.

## Eckdaten

| | |
| --- | --- |
| Endpunkt | `https://kraichtal-wetter.de/dashboard/api.php` |
| Methode | `GET` |
| Format | JSON, UTF-8 |
| Authentifizierung | Header `X-API-Key` |
| Key beantragen | <https://kraichtal-wetter.de/dashboard/apply.php> (kostenlos, sofort gültig) |
| Serverseitiger Cache | 5 Minuten |

Der Key gehört **ausschließlich** in den Header, nie in die URL — Begründung in `coordinator.py` bei `_split_api_key()`.

## Genutzte Sektionen

Ohne `section`-Parameter liefert die API **alle elf** Sektionen. Wir fordern gezielt an, was wir lesen (`REQUESTED_SECTIONS` in `coordinator.py`):

```
?section=current,days,hours
```

`meta` ist immer enthalten und darf nicht angefordert werden — wir nutzen daraus `meta.generated` als Anker für die Vorhersagedaten.

### `current` → Sensoren und aktuelle Wetterlage

| Feld | Verwendung |
| --- | --- |
| `temp`, `feels_like`, `dewpoint`, `humidity`, `pressure` | Sensoren; zusätzlich an der Wetter-Entität |
| `temp_source` | Attribut `source` am Sensor Außentemperatur: `live` = Messwert, `forecast` = Ersatzwert aus der Prognose |
| `wind`, `wind_dir`, `gust_max` | Sensoren; Wind auch an der Wetter-Entität |
| `solar` | Sensor |
| `rain` | Sensor „Station heute Niederschlag" — die **gemessene** Tagessumme, `total_increasing` |
| `tmin_today`, `tmax_today`, `rain_today` | Sensoren „Prognose Resttag …" — **Prognose**, nicht gemessen; ohne State-Class |
| `obs_date`, `obs_time`, `realtime` | Sensoren |
| `warnings` | Sensor (nur die Anzahl — siehe Backlog) |
| `icon` | Wetterlage der `weather`-Entität, über `ICON_MAP` |
| `station_today.tmax`, `.tmin`, `.gust`, `.wind_max`, `.press_max`, `.press_min` | Sensoren für die **gemessenen** Tagesextreme |
| `station_today.tmax_time`, `.tmin_time`, `.gust_time` | Attribut `time` am jeweiligen Station-Sensor — `"HH:MM"` in Ortszeit, unverändert durchgereicht |
| `station_today.gust_bft` | Attribut `beaufort` am Sensor „Station heute Böe" (Ganzzahl) |

#### Messung oder Prognose — die Namen führen in die Irre

- **`rain` ist gemessen**, und zwar die Tagessumme seit Mitternacht („Niederschlag heute (Station)" laut Doku) — kein Momentanwert. Sie steigt in den 0,2-mm-Schritten des Regenmessers und fällt um Mitternacht auf 0.
- **`rain_today`, `tmax_today` und `tmin_today` sind Prognosen** („Prognose für heute" laut Doku) — und zwar nur für die **verbleibenden** Stunden des Tages. Am 11.09.2026 um 23:00 enthielt `today.temp` nur noch Werte für 22 und 23 Uhr (13,5 und 12,4 °C); genau das waren `tmax_today` und `tmin_today`, während die Station 24,4 °C gemessen hatte und `days[0]` 24 °C vorhersagte.
- Die Prognose für den **ganzen** Tag steht in `days[0]`, die Messwerte in `station_today.*` und `rain`.

**Vom Betreiber bestätigt (17.09.2026)**, samt Mechanismus: `tmax_today`/`tmin_today` sind Maximum und Minimum über das Stundenarray des heutigen Tages, in dem bereits vergangene Stunden auf `null` stehen; die `null`-Werte fallen vor der Min/Max-Bildung heraus, übrig bleiben die noch nicht abgelaufenen Prognosestunden. `rain_today` ist entsprechend die Summe der Restmengen und fällt deshalb im Tagesverlauf, während `current.rain` als gemessene Tagessumme steigt. Der Betreiber bestätigt ausdrücklich, dass die drei Werte auf die Vorhersage-Seite gehören und nicht in die Langzeitstatistik — also genau die Korrektur aus 0.7.0 — und schärft die Beschreibung in seiner Doku nach.

**Gemessene Tageswerte für die Statistik** sind laut Betreiber: `current.temp` (mit `temp_source: "live"` als Beleg, dass es kein Prognose-Ersatzwert ist), `current.station_today.tmax`/`.tmin` für die gemessenen Tagesextreme mit Uhrzeit, und `current.rain` bzw. `rain.station.today` für den gemessenen Tagesregen. Alles davon nutzt die Integration bereits, bis auf die Sektion `rain` — die ist bewusst verworfen (siehe Backlog).

Bis 0.6.x hat die Integration `rain` und `rain_today` genau andersherum behandelt. Home Assistant schließt Prognosen ausdrücklich von `measurement` aus („not … a prediction of the future"), deshalb tragen die drei Prognose-Sensoren keine State-Class.

### `days` → Tagesvorhersage

Array mit 8 Einträgen, Index 0 = heute. Genutzt: `icon`, `tmax`, `tmin`, `pop`, `rain`, `wind`, `gust` (erwartete Spitzenböe), `wind_dir`. Nicht genutzt: `confidence`, `label`, `spark`.

`current.gust_max` gehört dagegen **nicht** an die Wetter-Entität: Es ist die stärkste Böe des bisherigen Tages, keine aktuelle. Eine aktuelle Böe liefert die API nicht.

Zwei dokumentierte Eigenheiten, die kein Bug sind:

- Das Tages-`icon` beschreibt die **Kernstunden 10–16 Uhr**. Es darf „bewölkt" zeigen, während `current.icon` gerade `sun` meldet.
- Bei Tag 0 gilt `tmin` für den ganzen Kalendertag, also auch für die bereits vergangene Nacht — der Wert kann tiefer liegen als alles, was noch kommt.
- `wind_dir` ist `null` bei Windstille.

Die Einträge enthalten **kein Datum**; wir leiten es aus `meta.generated` plus Index ab (siehe `_base_day()` in `weather.py`).

### `hours` → stündliche Vorhersage

12 Einträge für die nächsten Stunden. Genutzt: `icon`, `temp`, `pop`, `wind`. Eine Regenmenge und eine Windrichtung gibt es hier nicht.

**Die Einträge tragen kein Datum, nur eine Beschriftung:** `"Jetzt"` für den ersten, danach volle Stunden (`"00:00"`, `"01:00"` …) in Ortszeit, fortlaufend über Mitternacht. `_hourly_datetimes()` in `weather.py` macht daraus Zeitstempel:

- Verankert wird an der **ersten beschrifteten** Stunde — das ist die Aussage der API selbst. `meta.generated` entscheidet nur, zu welchem Tag diese Uhrzeit gehört. Sich auf `generated` zu verlassen hieße zu raten, ob die API `"Jetzt"` auf- oder abrundet.
- Ab dort wird **in UTC** weitergezählt, damit eine Stunde bei der Zeitumstellung eine Stunde bleibt.
- Widerspricht eine Beschriftung dem Schritt — eine Lücke in der Reihe —, gilt die Beschriftung, und es geht von dort weiter.

#### Zeitumstellung: was die API tatsächlich tut

**Vom Betreiber bestätigt (17.09.2026)** — vorher Annahme, jetzt aus der Datenebene beschrieben:

Die Stundenwerte liegen intern in **24 festen Slots pro Kalendertag**, indiziert nach der lokalen Stunde 0–23; `label` ist dieser Index als `%02d:00`. Eine 25. Stunde kann die Struktur gar nicht abbilden.

- **Oktober (doppelte Stunde):** Es gibt **genau ein** `"02:00"`, nie zwei. Liefert die Quelle (WXSIM) beide Instanzen, werden sie in **demselben Slot gemittelt**. Auf `"02:00"` folgt direkt `"03:00"`.
- **März (fehlende Stunde):** Der 02:00-Slot bleibt leer und fällt aus der Ausgabe heraus — auf `"01:00"` folgt `"03:00"`.
- **Die Reihe ist in diesen beiden Nächten nicht garantiert lückenlos.** Der interne Stundenzähler läuft durch die Wanduhr-Wiederholung hindurch weiter, während die Slots nur einmal 02:00 haben. An allen anderen Tagen des Jahres ist sie lückenlos.

`_hourly_datetimes()` kommt damit richtig zurecht, **ohne Änderung** — weil bei einem Widerspruch zwischen Schritt und Beschriftung die Beschriftung gilt. Mit den bestätigten Label-Reihen nachgerechnet (17.09.2026):

**Oktober, Nacht zum 25.10.2026** — ein `"02:00"`, danach `"03:00"`:

| Label | Zeitstempel | UTC | Anmerkung |
| --- | --- | --- | --- |
| `01:00` | `2026-10-25T01:00:00+02:00` | 23:00 | — |
| `02:00` | `2026-10-25T02:00:00+02:00` | 00:00 | erster Durchlauf der doppelten Stunde |
| `03:00` | `2026-10-25T03:00:00+01:00` | 02:00 | **zwei Stunden später** — der Sprung in den Daten |
| `04:00` | `2026-10-25T04:00:00+01:00` | 03:00 | Reihe wieder normal |

**März, Nacht zum 29.03.2026** — `"02:00"` fehlt:

| Label | Zeitstempel | UTC | Anmerkung |
| --- | --- | --- | --- |
| `01:00` | `2026-03-29T01:00:00+01:00` | 00:00 | — |
| `03:00` | `2026-03-29T03:00:00+02:00` | 01:00 | eine Stunde später, die 02:00 gibt es nicht |
| `04:00` | `2026-03-29T04:00:00+02:00` | 02:00 | Reihe wieder normal |

In beiden Fällen sind die Zeitstempel eindeutig und steigen streng — keine Dubletten, kein Rückwärtssprung. Home Assistant sortiert sie also sauber ein. Der reale Abstand zwischen zwei Einträgen entspricht dem Sprung in den Daten, nicht stur einer Stunde; das ist die richtige Wiedergabe dessen, was die API liefert.

**Die verbleibende Unschärfe, bewusst in Kauf genommen:** Der eine 02:00-Eintrag im Oktober bekommt den Zeitpunkt des *ersten* Durchlaufs (`+02:00`). Enthält der Slot gemittelte Werte oder den zweiten Durchlauf, ist dieser eine Eintrag um eine Stunde zu früh angesetzt. Das betrifft höchstens einen von zwölf Einträgen, in einer Nacht im Jahr, und lässt sich aus den Daten heraus nicht auflösen.

#### Angekündigt, von uns nicht genutzt: ein Feld `time` je Stundeneintrag

Der Betreiber hat auf unsere Anregung hin zugesagt (17.09.2026, am 24.09.2026 noch nicht live): neben `label` steht künftig `time` mit ISO 8601 samt Offset, z. B. `"2026-10-25T02:00:00+02:00"`. `label` bleibt unverändert.

**Die Integration nutzt es bewusst nicht** (entschieden 24.09.2026). Die Rückrechnung oben ist gegen die Antwort des Betreibers geprüft und verkraftet beide Umstellungsnächte; `time` würde das Ergebnis nur an diesen zwei Nächten im Jahr berühren. Die Einschränkung aus der Slot-Struktur bliebe ohnehin: Der eine 02:00-Eintrag im Oktober trüge **einen** Zeitstempel, nicht zwei, und im März fehlt 02:00 im Zeitstempel wie im Label. Taucht das Feld auf, wird es wie jedes andere ungenutzte Feld ignoriert.

Nicht zu verwechseln mit `current.obs_date`/`obs_time`: Das ist die Uhrzeit der letzten Stationsmessung (`"07:50"`, ohne Offset, als Sensor „Beobachtungszeit" angelegt), keine Zeitangabe für die Vorhersagestunden. Den Tagesanker für `hours` liefert `meta.generated`, das Datum und Offset trägt.

## Wettersymbole

Genau 19 Codes, vollständig in `ICON_MAP` (`weather.py`) abgebildet — gegen die Dokumentation geprüft, keine Abweichung.

**Alle vier Gewitter-Codes führen Regen.** `storm` ist das *schwache* Gewitter, nicht das trockene; ein Gewitter ohne Niederschlag existiert nicht. Deshalb ist der HA-Zustand `lightning` über diese Quelle unerreichbar.

Tag/Nacht-Varianten gibt es nur bei klar (`sun`/`moon`) und leicht bewölkt (`suncloud`/`mooncloud`). Regen, Schnee, Gewitter und Nebel kommen nachts unter demselben Code.

**Nicht erreichbare HA-Zustände** — mangels Code, nicht aus Nachlässigkeit: `hail` und `windy`/`windy-variant` (stecken in den Warn- bzw. Windfeldern), `snowy-rainy` (Schneeregen läuft unter `snow`), `lightning` (siehe oben) und `exceptional`.

## Fehlerbehandlung

Zuerst immer `ok` prüfen; bei `false` steht der Grund in `error`.

| Status | Bedeutung | Unser Verhalten |
| --- | --- | --- |
| 401 | Schlüssel fehlt | `ConfigEntryAuthFailed` → Reauth-Dialog |
| 403 | Schlüssel ungültig oder gesperrt | `ConfigEntryAuthFailed` → Reauth-Dialog |
| 400 / 404 / 405 / 500 | Anfrage, Sektion, Methode, Server | `UpdateFailed` mit Klartext |
| 304 | Unverändert (nur mit `If-None-Match`) | wird derzeit nicht genutzt |

Die Dokumentation ist ausdrücklich: Bei 401/403 hilft kein erneuter Versuch. Genau deshalb lösen beide den Reauth-Flow aus, statt in einer Schleife weiterzufragen. Der Text aus `error` und die Bedeutung des Status-Codes landen im Sensor **API-Status**, damit die Ursache am Gerät sichtbar ist.

## Fair use

Die Antwort wird serverseitig fünf Minuten zwischengespeichert; häufiger abzufragen liefert dieselben Daten (erkennbar an `meta.cached`). Empfehlung der Doku: `current` alle 1–5 Minuten, `days` und `alerts` alle 15–30 Minuten.

Die Integration erzwingt deshalb ein Mindestintervall von **300 Sekunden** (`MIN_SCAN_INTERVAL`), sowohl in beiden Dialogen als auch beim Start für Bestandseinträge.

## Nicht genutzte Sektionen — Backlog

Bewusst nicht angefordert. Wer eine davon braucht, muss sie zu `REQUESTED_SECTIONS` hinzufügen. Reihenfolge, Stand und Entscheidungen stehen in [`Plan.md`](../Plan.md); hier nur, was die API dazu hergibt.

| Sektion | Inhalt | Einschätzung |
| --- | --- | --- |
| `alerts` | DWD-Warnungen mit `title`, `event`, `sev`, `level`, `active`, `desc`, `time` | **Verworfen.** Dafür gibt es die Core-Integration „Deutscher Wetterdienst (DWD) Weather Warnings": Sie holt dieselben Warnungen direkt beim DWD, je Warnung mit `headline`, `description`, `instruction` sowie `start_time`/`end_time` als echten Zeitstempeln, und trennt aktuelle Warnstufe von Vorwarnstufe. Hier gibt es die Gültigkeit nur als Fließtext, keine Verhaltenshinweise und kein Vorwarn-Konzept. Der Sensor „Warnungen" aus `current.warnings` bleibt als reine Anzahl. |
| `today` | 24 Stundenwerte des heutigen Tages (`temp`, `rain`, `snow`, `wind`, `gust`) | Für Diagramme gedacht; in HA über die Sensorhistorie bereits abgedeckt. |
| `trend` | Wie `days`, aber mit Modellspannbreite (`lo`/`avg`/`hi`) | Kein HA-Gegenstück im Wetter-Modell. |
| `models` | Einzelmodelle, Streuung, `confidence` | Nische. |
| `astro` | Sonnenauf-/-untergang, Mondphase | Deckt HA über `sun.sun` und die Mond-Integration bereits ab. |
| `climate` | Kenntage, Jahresextreme, Stationsrekorde | Umfangreich; ein- bis zweimal täglich abzurufen, passt nicht zum Poll-Intervall der Integration. |
| `rain` | Bilanz heute/gestern/Monat/Jahr inkl. Abweichung vom Klimamittel | **Verworfen.** Monats- und Jahressummen bildet Home Assistant seit 0.7.0 selbst aus `current.rain` (`total_increasing`). Eigenständig blieben nur `expected`, `annual_avg`, `delta`, Werte aus der Zeit vor der Installation und `station.h24` (letzte 24 Stunden, nicht dokumentiert) — zu wenig für den zweiten, langsamen Abruf, den die Sektion laut Fair use bräuchte. |

## Weitere Punkte

- **ETag / `If-None-Match` — geprüft und verworfen:** Jede Antwort trägt ein ETag; mit `If-None-Match` gäbe es bei unveränderten Daten ein `304` ohne Inhalt. Bei unserem Takt kommt das praktisch nie vor: Die Station liefert alle paar Minuten neue Werte, der Server cached fünf Minuten, und wir fragen frühestens alle fünf Minuten. Kein Gewinn für zusätzliche Fehlerpfade.
