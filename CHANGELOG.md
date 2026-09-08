# Changelog

Alle signifikanten Änderungen an dieser Integration werden hier festgehalten.

## [0.5.5] - 2026-09-08
### Hinzugefügt
- `wind_dir` hat jetzt `device_class: wind_direction` und
  `state_class: measurement_angle`. Der Grund, aus dem der Sensor bisher ohne
  State-Class blieb — der Mittelwert einer zirkulären Größe über 0°/360° ist
  sinnlos — ist genau das, was `measurement_angle` löst: Home Assistant
  bildet einen zirkulären Mittelwert, ein um Nord pendelnder Wind mittelt
  also nicht mehr auf Süd. Damit entsteht für die Windrichtung erstmals eine
  brauchbare Langzeitstatistik. HA erzwingt diese Kombination: zu
  `wind_direction` ist keine andere State-Class und keine andere Einheit als
  `°` zulässig.

### Geändert
- Nur Kommentar, kein Verhalten: an `rain_today` steht jetzt, warum
  `total_increasing` dort korrekt ist und die Recorder-Warnung „state is not
  strictly increasing" kein Grund ist, das zu ändern.

### Bekannt
- Die übrigen „today"-Sensoren (`tmax_today`, `tmin_today`,
  `station_today.*`) sind Tagesaggregate und damit streng genommen keine
  Messwerte „in present time", wie es die Definition von `measurement`
  verlangt. Die HA-Doku nennt für Tages-Min/Max keine Alternative, und ein
  Entfernen der State-Class würde die bereits aufgezeichnete
  Langzeitstatistik dieser Entitäten entwerten. Sie bleiben daher auf
  `measurement`; der einzige praktische Nachteil ist eine wenig aussagekräftige
  `mean`-Statistik.

## [0.5.4] - 2026-09-08
### Behoben
- `ICON_MAP` folgt jetzt durchgehend einer Regel, statt drei Einträge
  abweichen zu lassen. Maßgeblich ist, was das jeweilige Icon tatsächlich
  zeichnet: Der Sonnen-/Mondanteil eines `sun*`/`moon*`-Codes ist kein
  eigenes Wetter und entfällt, die Niederschlagsart entscheidet; zeichnet ein
  Icon Blitz *und* Tropfen, behält die Bedingung beides. Konkret geändert:
  - `sunsnow`: `snowy-rainy` → `snowy` (in 0.5.3 falsch ergänzt — das Icon
    enthält ausschließlich Schneeflocken, keinen Regentropfen; `snowy-rainy`
    bedeutet in HA Schneeregen).
  - `sunstorm`: `lightning-rainy` → `lightning` (Icon zeigt Sonne, Wolke und
    Blitz, aber keine Tropfen).
  - `storm-rain`: `pouring` → `lightning-rainy` (Icon zeigt Blitz *und*
    Tropfen; der Blitz ging in der Bedingung bisher verloren).
  Die beiden letzten Einträge stammen aus der Zeit vor 0.5.3 und waren mit
  `storm` → `lightning` bzw. `storm-svr` → `lightning-rainy` nicht vereinbar:
  gleiche Bildzusammensetzung, unterschiedliche Bedingung. Die Regel steht
  jetzt als Kommentar über `ICON_MAP`, damit sie bei künftigen Ergänzungen
  nicht wieder auseinanderläuft.

## [0.5.3] - 2026-09-07
### Behoben
- `ICON_MAP` in `weather.py` deckte nur 9 der tatsächlich möglichen API-Icons
  ab, u. a. fehlten `sun` und `moon` für klaren Himmel — dadurch stand die
  aktuelle Wetterlage bei Sonnenschein bzw. klarer Nacht auf `unknown`
  (in der UI „Unbekannt"), genau wie im „Bekannt"-Abschnitt von 0.5.2
  angekündigt. Die vollständige Icon-Liste wurde gegen das SVG-Icon-Register
  des öffentlichen Dashboards (`const I = {...}` auf
  kraichtal-wetter.de/dashboard/) verifiziert und deckt jetzt alle 18 dort
  registrierten Codes ab: neu hinzugekommen sind `sun` → `sunny`,
  `moon` → `clear-night`, `drizzle` und `sunrain` → `rainy`,
  `storm-svr` → `lightning-rainy`, `snow-lgt`/`snow`/`snow-hvy` → `snowy`
  sowie `sunsnow` → `snowy-rainy`.

### Bekannt
- Nebel, Hagel und Wind haben im Dashboard-Icon-Register kein eigenes Icon
  und bleiben daher weiterhin unabgedeckt — dafür existiert offenbar kein
  API-Icon-Code, keine geratene Bedingung.

## [0.5.2] - 2026-08-28
### Behoben
- Wetterlage stand nachts sowie an einzelnen Vorhersagetagen auf `unknown`
  bzw. `condition: null`. Ursache: `ICON_MAP` in `weather.py` deckte nicht
  alle von der API gelieferten Icon-Codes ab — `_condition()` gab für einen
  unbekannten Code bewusst `None` zurück (kein Bug, sondern die 0.5.0-Absicht,
  keine falsche Bedingung zu raten), aber die fehlenden Codes wurden nie
  ergänzt. Live gegen die Produktions-API verifiziert: `mooncloud` (Nacht-
  Pendant zu `suncloud`) für die aktuelle Bedingung sowie `rain` und
  `rain-hvy` für die Tagesvorhersage. Alle drei sind jetzt auf
  `partlycloudy`, `rainy` bzw. `pouring` gemappt.
- Ein unbekannter Icon-Code wird jetzt einmalig als `WARNING` geloggt statt
  ausschließlich als `DEBUG` (das nur sichtbar ist, wenn Debug-Logging für
  die Integration bereits vorher aktiviert wurde). Wiederholungen desselben
  Codes bleiben `DEBUG`, um das Log bei einem dauerhaft unbekannten Code
  nicht mit einem Eintrag pro Abrufintervall zu fluten.

### Bekannt
- `ICON_MAP` deckt weiterhin nur die bisher tatsächlich beobachteten
  API-Icons ab (6 von 15 möglichen HA-Wetterbedingungen). Insbesondere für
  klaren Himmel (`sunny`/`clear-night`) gibt es noch keinen Icon-Code im
  Mapping — ein wolkenloser Tag oder eine klare Nacht zeigt bis dahin
  weiterhin `unknown`, jetzt aber sichtbar per `WARNING` statt lautlos.
  Schnee, Nebel, Hagel und Wind sind ebenfalls noch nicht abgedeckt.

## [0.5.1] - 2026-08-19
### Geändert
- **Der API-Key wird jetzt als `X-API-Key`-Header übertragen statt als `key`-Query-Parameter.** Damit ist die Ursache des Log-Lecks beseitigt statt nur abgefangen: `aiohttp.ClientResponseError` bettet die Request-URL in seine String-Repräsentation ein, Header dagegen nicht. Der Key kann so über keinen Traceback, keine Exception-Chain und kein Debug-Logging der HTTP-Ebene mehr austreten — auch nicht über Code, der erst künftig hinzukommt.
  - Ein in der konfigurierten URL hinterlegter Key (`key`, `api_key`, `apikey`) wird beim Start ausgelesen und ebenfalls in den Header verschoben; die URL wird davon bereinigt. Kein Codepfad setzt den Key noch in eine URL.
  - Bewusst **ohne** Rückfall auf den Query-Parameter: Genau dieser Pfad wäre der undichte. Sollte der Header serverseitig entfallen, quittiert die API das mit 401 und der Reauth-Dialog geht auf — sichtbar statt still.
  - Die defensiven Vorkehrungen aus 0.4.5 (kein `err` im Log, `from None`) bleiben als zweite Ebene bestehen.
- `AUTH_ERROR_STATUSES` gegen die API verifiziert: 401 bei fehlendem, 403 bei ungültigem Key — beide lösen den Reauth-Flow aus.

## [0.5.0] - 2026-08-19
### Geändert (Breaking)
- **Entity-IDs der Sensoren umgestellt.** Bisher erzeugte Home Assistant sie aus den fest im Code stehenden deutschen Namen (`sensor.kraichtal_wetter_boen_max`, `sensor.kraichtal_wetter_gefuhlt`). Die Namen liegen jetzt in `translations/`, wodurch die IDs aus den sprachunabhängigen englischen Namen entstehen (`sensor.kraichtal_wetter_max_gust`, `sensor.kraichtal_wetter_feels_like`). Vollständige Zuordnung in der README.
  - Bestehende Entitäten werden beim ersten Start automatisch umbenannt, die Recorder-Historie bleibt damit erhalten. Entitäten, deren ID von Hand geändert wurde, bleiben unangetastet.
  - **Eigene Dashboards, Automationen, Skripte und Templates müssen manuell angepasst werden** — Home Assistant schreibt Verweise dort nicht mit um.
- Sensornamen werden über `translation_key` aufgelöst; die Anzeige folgt jetzt der Home-Assistant-Sprache (Deutsch und Englisch enthalten) statt fest deutsch zu sein.
- **Die Wetter-Entität ist jetzt die primäre Entität des Geräts** und heißt `weather.kraichtal_wetter` statt `weather.kraichtal_wetter_forecast`; als Anzeigename trägt sie nur noch „Kraichtal Wetter". Sie wird von derselben automatischen Umbenennung erfasst wie die Sensoren.

## [0.4.5] - 2026-08-19
### Behoben
- Sicherheitsfix (Nachtrag zu 0.4.4): Der API-Key konnte weiterhin über die Exception-Chain austreten. `UpdateFailed` wurde mit `from err` geworfen, wodurch die ursprüngliche `ClientResponseError` als `__cause__` erhalten blieb — inklusive der vollständigen URL mit `key`-Parameter in ihrer String-Repräsentation. Wird die Kette irgendwo mit `exc_info=True` ausgegeben, landet der Key doch im Log. Jetzt `from None`.
- Reauth-Flow war nicht erreichbar: HTTP 401/403 wurde als `UpdateFailed` behandelt, sodass ein ungültiger API-Key nur endlos Fehler protokollierte, statt den vorhandenen „API-Key aktualisieren"-Dialog zu öffnen. Diese Status-Codes lösen nun `ConfigEntryAuthFailed` aus.
- `DataUpdateCoordinator` wird mit `config_entry=entry` erzeugt — ohne diese Zuordnung kann der Coordinator den Reauth-Flow gar nicht starten.
- Ungültige Wetterbedingung: `"sunstorm"` war auf `"storm"` gemappt, was keine gültige Home-Assistant-Bedingung ist und in der UI nicht dargestellt wurde. Jetzt `"lightning-rainy"`.
- Forecast-Cache wurde nie invalidiert: Die Invalidierung hing an `async_update()`, das bei `CoordinatorEntity` wegen `should_poll = False` nie aufgerufen wird. Die Vorhersage blieb dadurch dauerhaft auf dem ersten Abruf stehen (die aktuellen Messwerte waren korrekt, was den Fehler verdeckt hat). Läuft jetzt über `_handle_coordinator_update()`.
- Forecast-Zeitzone: Der UTC-Offset `+00:00` wurde unabhängig von der tatsächlichen Zeitzone von `meta.generated` fest an den Zeitstempel gehängt. Umgestellt auf `dt_util.start_of_local_day()` pro Tag, wodurch auch Sommerzeit-Wechsel korrekt behandelt werden.
- `translations/de.json` und `translations/en.json` ergänzt. Home Assistant lädt bei Custom Integrations zur Laufzeit ausschließlich `translations/`; die Texte aus `strings.json` waren in der Oberfläche wirkungslos.
- Entity-IDs in README und Lovelace-Beispiel korrigiert: Dokumentiert waren durchgängig die API-Feldnamen (`sensor.kraichtal_wetter_temp`), tatsächlich erzeugt Home Assistant die IDs aus den deutschen Anzeigenamen (`sensor.kraichtal_wetter_aussentemperatur`). Betraf alle 22 Sensoren.

### Hinzugefügt
- `state_class` für alle numerischen Sensoren, damit Home Assistant Langzeitstatistiken aufzeichnet (`measurement`, für `rain_today` `total_increasing`). `wind_dir` bleibt bewusst ohne, da Mittelwerte über den 0°/360°-Übergang keine sinnvollen Werte ergeben.
- Passende `device_class`-Angaben für Wind, Solarstrahlung und Niederschlag; Einheiten und Geräteklassen durchgängig über HA-Enums statt String-Literale.
- `.gitignore` (u. a. `__pycache__/`).
- `country: "DE"` in `hacs.json` — laut HACS-Aufnahmekriterien anzugeben, wenn ein Repository nur ein einzelnes Land bedient.
- `.github/workflows/validate.yml`: HACS-Action und Hassfest, beides Voraussetzung für die Aufnahme in den HACS-Standardkatalog.
- `LICENSE` (MIT) — bis dahin galt trotz öffentlichem Repository das Standard-Urheberrecht, eine Nachnutzung war damit formal nicht gestattet. Die HACS-Action prüft inzwischen auf eine Lizenz.
- `issue_tracker` im Manifest — Pflichtfeld der HACS-Manifestprüfung, fehlte bisher.

### Behoben (Build)
- Manifest-Keys nach Hassfest-Vorgabe sortiert (`domain`, `name`, danach alphabetisch).
- `actions/checkout` von v4 auf v5 gehoben; v4 löste die Node-20-Deprecation-Warnung der GitHub-Runner aus.

### Entfernt
- `custom_components/kraichtal_wetter/README.md`: wurde von nichts ausgeliefert (HACS rendert das Root-README), enthielt die veralteten Entity-IDs und beschrieb eine YAML-Konfiguration über `configuration.yaml`, die die Integration nie unterstützt hat — ein dort hinterlegter API-Key wurde wirkungslos ignoriert.
- `scripts/generate_logo.py`: nicht lauffähig (schrieb nach `custom_components/kraichtal_wetter_api/`, das seit 0.2.0 nicht mehr existiert), benötigte ein nirgends deklariertes Pillow und erzeugte redundante Kopien der Brand-Icons.

### Geändert
- Unbekannte Icon-Namen liefern jetzt `None` statt `"sunny"` — eine unbekannte Bedingung wurde vorher als „sonnig" ausgegeben. Unbekannte Icons werden auf Debug-Level protokolliert.
- Überflüssiges `async_setup` und ein zu breites `except Exception` in `async_setup_entry` entfernt; letzteres hätte `ConfigEntryAuthFailed` beim Setup verschluckt.
- HTTP-Timeout als `aiohttp.ClientTimeout` statt als nackter Zahl; Response wird als Context-Manager verwendet.
- Entitäten nutzen `_attr_has_entity_name` (bestehende Entity-IDs bleiben unverändert).

## [0.4.4] - 2026-08-13
### Behoben
- Sicherheitsfix: API-Key konnte bei HTTP-Fehlern über `home-assistant.log` geleakt werden, da `aiohttp.ClientResponseError` die vollständige Request-URL (inkl. `key`-Query-Parameter) in seiner String-Repräsentation enthält. `coordinator.py` loggt seitdem nur noch Status und `err.message` statt die Exception selbst. (Unvollständig — siehe 0.4.5.)

## [0.4.3] - 2026-08-11
### Geändert
- README: Hinweis unter dem „In Home Assistant öffnen"-Button ergänzt, dass der Browser die Instanz-URL merkt und diese bei geändertem Port (z. B. Standard-Port 80 statt `:8123`) über das Stift-Symbol auf der my.home-assistant.io-Seite korrigiert werden muss.

## [0.4.2] - 2026-08-11
### Hinzugefügt
- `brand/`-Ordner vervollständigt: 8 Brand-Bilder (icon/logo + `@2x`-Varianten + `dark_*`-Varianten) für lokale Auslieferung über die Brands Proxy API (HA 2026.3+).
- README um `HACS-Custom`-Badge und Installationsanleitung über HACS inkl. „In Home Assistant öffnen"-Button ergänzt.

## [0.4.1] - 2026-07-17
### Hinzugefügt
- `hacs.json` im Repository-Root für korrekte HACS-Erkennung hinzugefügt.

### Entfernt
- Ungenutzte Bilddateien `logo.png` und `dark_logo.png` aus dem Integration-Root entfernt (nur `brand/` wird verwendet).
- Ungenutzte `logo.svg` aus dem Repository-Root entfernt.

## [0.4.0] - 2026-07-17
### Geändert
- Forecast-Implementierung auf `async_forecast_daily()` umgestellt (deprecated `forecast` Property entfernt).
- Forecast-Felder auf `native_`-Präfix umgestellt (`native_temperature`, `native_templow`, `native_wind_speed`).
- `native_temperature_unit` und `native_pressure` als Properties hinzugefügt.
- `wind_bearing` und `native_wind_speed` als separate Properties hinzugefügt.

### Behoben
- Forecast-Datum wird nun korrekt aus `meta.generated` + Tages-Index generiert (RFC 3339 UTC).
- API liefert kein `date`-Feld im `days`-Array – jetzt aus `meta.generated` berechnet.
- Forecast-Caching eingeführt; Cache wird bei Coordinator-Update invalidiert.

## [0.3.0] - 2026-07-17
### Geändert
- `iot_class` von `local_polling` zu `cloud_polling` korrigiert.
- Unnötigen `importlib`-basierten Platform-Import entfernt (`async_forward_entry_setups` übernimmt dies).
- Beim ersten Refresh wird nun `ConfigEntryNotReady` statt `UpdateFailed` geworfen, sodass HA den Setup-Vorgang automatisch erneut versucht.
- Custom Attributes auf dem `DataUpdateCoordinator` (`entry_id`, `api_url`) entfernt; `entry` wird stattdessen über `hass.data` weitergegeben.
- Redundantes `available`-Property in `KraichtalWetterSensor` entfernt (wird von `CoordinatorEntity` geerbt).
- Deprecated `CONNECTION_CLASS` im Config Flow entfernt.
- Unbenutzte Imports in `coordinator.py` bereinigt.
- URL-Key-Anhänge-Logik durch korrekte URL-Parsung via `urllib.parse` ersetzt.

### Hinzugefügt
- Reauth-Flow: API-Key kann über die UI aktualisiert werden, wenn der aktuelle nicht mehr funktioniert.
- Options Flow: Abfrageintervall (`scan_interval`) kann nach der Installation geändert werden.
- Null-Schutz in `weather.py` für `coordinator.data` und `current`.
- `native_wind_speed_unit_of_measurement` in der Weather-Entität gesetzt.
- Forecast verwendet `date`-Feld der API als `datetime` (funktionierte nicht korrekt, siehe 0.4.0).
- Eindeutige `unique_id` zur Vermeidung doppelter Konfigurationen.

### Entfernt
- Unnötiges `import_executor` aus `manifest.json` entfernt.

## [0.2.3] - 2026-07-14
### Geändert
- Icon hinzugefügt

## [0.2.2] - 2026-07-14
### Geändert
- Rebranding finalisiert
- Release ready

## [0.2.1] - 2026-07-14
### Geändert
- Rebranding finalisiert
- Release ready

## [0.2.0] - 2026-07-14
### Geändert
- Integration umbenannt und als `Kraichtal Wetter` angezeigt.
- Alle `kraichtal_wetter`-Entitäten werden nun als ein Gerät in der Integrationen-Übersicht gruppiert.
- Erweiterung der Sensorabdeckung um zusätzliche API-Felder wie `dewpoint`, `wind_dir`, `tmax_today`, `tmin_today`, `rain_today`, `warnings`, `obs_date`, `obs_time`, `realtime` und `station_today.*`.
- Fix: Nested current-Felder über `station_today.*` korrekt aufgelöst.

## [0.0.2] - 2026-07-14
### Geändert
- Konfigurationsfeld von `api_key` zu `key` umgestellt (abwärtskompatibel).
- Korrekte Anhängung des API-Parameters `key=` an die URL.
- Integration-Icon als `logo.png` hinzugefügt.

## [0.0.1] - 2026-07-14
### Hinzugefügt
- Erste Version der Home Assistant Custom Integration für die Kraichtal Wetter API.
- Unterstützung einer `config_flow`-basierten Einrichtung.
- Erste Sensor-Entitäten und `weather.kraichtal_wetter_forecast`.

