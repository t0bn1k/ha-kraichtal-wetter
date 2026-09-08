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
?section=current,days
```

`meta` ist immer enthalten und darf nicht angefordert werden — wir nutzen daraus `meta.generated` als Anker für die Vorhersagedaten.

### `current` → Sensoren und aktuelle Wetterlage

| Feld | Verwendung |
| --- | --- |
| `temp`, `feels_like`, `dewpoint`, `humidity`, `pressure` | Sensoren; zusätzlich an der Wetter-Entität |
| `wind`, `wind_dir`, `gust_max` | Sensoren; Wind auch an der Wetter-Entität |
| `solar`, `rain`, `rain_today` | Sensoren |
| `tmin_today`, `tmax_today` | Sensoren (**Prognose** für heute, nicht gemessen) |
| `obs_date`, `obs_time`, `realtime` | Sensoren |
| `warnings` | Sensor (nur die Anzahl — siehe Backlog) |
| `icon` | Wetterlage der `weather`-Entität, über `ICON_MAP` |
| `station_today.*` | Sensoren für die **gemessenen** Tagesextreme |

Wichtig: `tmax_today` ist der *erwartete*, `station_today.tmax` der *gemessene* Höchstwert. Dass beide abweichen, ist normal.

### `days` → Tagesvorhersage

Array mit 8 Einträgen, Index 0 = heute. Genutzt: `icon`, `tmax`, `tmin`, `pop`, `rain`, `wind`, `wind_dir`.

Zwei dokumentierte Eigenheiten, die kein Bug sind:

- Das Tages-`icon` beschreibt die **Kernstunden 10–16 Uhr**. Es darf „bewölkt" zeigen, während `current.icon` gerade `sun` meldet.
- Bei Tag 0 gilt `tmin` für den ganzen Kalendertag, also auch für die bereits vergangene Nacht — der Wert kann tiefer liegen als alles, was noch kommt.
- `wind_dir` ist `null` bei Windstille.

Die Einträge enthalten **kein Datum**; wir leiten es aus `meta.generated` plus Index ab (siehe `_base_day()` in `weather.py`).

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

Bewusst nicht angefordert. Wer eine davon braucht, muss sie zu `REQUESTED_SECTIONS` hinzufügen.

| Sektion | Inhalt | Einschätzung |
| --- | --- | --- |
| `hours` | Nächste 12 Stunden mit `temp`, `pop`, `wind`, `icon` | **Vorgemerkt:** Grundlage für `FORECAST_HOURLY`. Haken: Die Einträge tragen nur ein `label` („Jetzt", „15:00"), keinen Zeitstempel — die Zeit müsste wie bei `days` aus `meta.generated` rekonstruiert werden, inklusive Mitternachtswechsel und Sommerzeitumstellung. |
| `alerts` | DWD-Warnungen mit `title`, `event`, `sev`, `level`, `active`, `desc`, `time` | **Vorgemerkt:** Unser `warnings`-Sensor liefert bisher nur die Anzahl aus `current.warnings`. Die Einzelwarnungen als Attribute daran wären deutlich nützlicher. Fair-use-Intervall: 15–30 Minuten. |
| `today` | 24 Stundenwerte des heutigen Tages (`temp`, `rain`, `snow`, `wind`, `gust`) | Für Diagramme gedacht; in HA über die Sensorhistorie bereits abgedeckt. |
| `trend` | Wie `days`, aber mit Modellspannbreite (`lo`/`avg`/`hi`) | Kein HA-Gegenstück im Wetter-Modell. |
| `models` | Einzelmodelle, Streuung, `confidence` | Nische. |
| `astro` | Sonnenauf-/-untergang, Mondphase | Deckt HA über `sun.sun` und die Mond-Integration bereits ab. |
| `climate` | Kenntage, Jahresextreme, Stationsrekorde | Umfangreich; ein- bis zweimal täglich abzurufen, passt nicht zum Poll-Intervall der Integration. |
| `rain` | Bilanz heute/gestern/Monat/Jahr inkl. Abweichung vom Klimamittel | Denkbar als zusätzliche Sensoren (Monats-/Jahressumme). |

## Weitere vorgemerkte Punkte

- **`current.temp_source`** unterscheidet `live` (echter Messwert) von `forecast` (Ersatzwert aus der Prognose). Unser Temperatursensor macht diesen Unterschied bisher nicht sichtbar — als Attribut wäre er ehrlicher.
- **`station_today` hat mehr Felder als wir nutzen:** `wind_max` (höchster Wind), die Uhrzeiten zu den Extremwerten (`tmax_time`, `tmin_time`, `gust_time`) und die Böe in Beaufort (`gust_bft`).
- **ETag / `If-None-Match`:** Jede Antwort trägt ein ETag; mit `If-None-Match` gäbe es bei unveränderten Daten ein `304` ohne Inhalt. Spart Übertragung, erfordert aber, den letzten Datenstand über den Fehlerfall hinweg zu halten.
