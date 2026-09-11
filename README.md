# Kraichtal Wetter

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg?style=for-the-badge)](https://github.com/hacs/integration)
[![Release](https://img.shields.io/github/v/release/t0bn1k/ha-kraichtal-wetter?style=for-the-badge)](https://github.com/t0bn1k/ha-kraichtal-wetter/releases)
[![Lizenz](https://img.shields.io/github/license/t0bn1k/ha-kraichtal-wetter?style=for-the-badge)](LICENSE)
[![Validate](https://img.shields.io/github/actions/workflow/status/t0bn1k/ha-kraichtal-wetter/validate.yml?style=for-the-badge&label=validate)](https://github.com/t0bn1k/ha-kraichtal-wetter/actions/workflows/validate.yml)

Kraichtal Wetter ist eine Home Assistant Custom Integration, die aktuelle Wetterdaten aus der Kraichtal Wetter API als Sensoren und als `weather`-Entität bereitstellt.

Datenquelle: https://kraichtal-wetter.de

## API-Key beantragen

Die Integration benötigt einen eigenen API-Key — ohne Key beantwortet die API keine Anfrage. Der Schlüssel ist kostenlos und wird über ein kurzes Formular ausgestellt: https://kraichtal-wetter.de/dashboard/apply.php

Auszufüllen sind drei Felder:

| Feld | Was hineingehört |
| --- | --- |
| Name oder Verwendungszweck | Damit der Betreiber Zugriffe zuordnen kann, z. B. `Home-Assistant Müller` |
| Kontakt-E-Mail | Nur für Rückfragen, falls es Probleme mit dem Zugang gibt |
| Sicherheitsfrage | Eine einfache Rechenaufgabe als Schutz gegen automatisierte Anfragen |

Den Schlüssel gibst du anschließend beim Einrichten der Integration ein. Er lässt sich jederzeit über `Einstellungen → Geräte & Dienste → Kraichtal Wetter → Konfiguration` ändern.

## Installation

### Installation über HACS

1. Öffne in Home Assistant `HACS → Integrationen`.
2. Füge über `⋯ → Benutzerdefinierte Repositorys` die URL `https://github.com/t0bn1k/ha-kraichtal-wetter` mit Kategorie `Integration` hinzu.
3. Suche nach `Kraichtal Wetter`, lade die Integration herunter und starte Home Assistant neu.
4. Füge die Integration über den Button unten oder `Einstellungen → Geräte & Dienste → Integration hinzufügen` hinzu:

   [![Open your Home Assistant instance and start setting up a new integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=kraichtal_wetter)

   > **Hinweis:** Der Button merkt sich deine Home-Assistant-Instanz-URL im Browser. Läuft deine Instanz über einen anderen Port als zuvor (z. B. Standard-Port 80 statt `:8123`), öffnet der Button eine veraltete URL. Korrigiere sie dann über das Stift-Symbol auf der geöffneten my.home-assistant.io-Seite.

> **Hinweis für bestehende Installationen:** Das Repository hieß bis 0.6.1 `kraichtal-wetter-hacs`. HACS verlangt für die Aufnahme in den Standardkatalog, dass „HACS" nicht im Repository-Namen vorkommt. GitHub leitet die alte Adresse automatisch weiter, installierte Integrationen laufen unverändert weiter — an Entitäten, Konfiguration und Historie ändert sich nichts. Sollte HACS für dich keine Updates mehr finden, entferne das benutzerdefinierte Repository einmal und füge es unter der neuen URL wieder hinzu; die Integration bleibt dabei installiert.

### Manuelle Installation

1. Kopiere den Ordner `custom_components/kraichtal_wetter` in dein Home Assistant `custom_components`-Verzeichnis.
2. Starte Home Assistant neu.
3. Öffne `Einstellungen → Geräte & Dienste → Integration hinzufügen`.
4. Suche nach `Kraichtal Wetter`.
5. Folge dem UI-Setup und gib deinen API-Key ein.

## Was bietet Kraichtal Wetter?

- Aktuelle Wetterdaten aus der Kraichtal Wetter API
- Forecast über `weather.kraichtal_wetter`
- Erweiterte Sensoren aus `station_today`
- Gruppierte Entitäten unter einem Gerät in der Integrationen-Ansicht

## Unterstützte Entitäten

Die Entity-IDs sind sprachunabhängig (englisch), die Anzeigenamen folgen der eingestellten Home-Assistant-Sprache:

| Entität | Anzeige (Deutsch) | API-Feld |
| --- | --- | --- |
| `weather.kraichtal_wetter` | Kraichtal Wetter | – |
| `sensor.kraichtal_wetter_outdoor_temperature` | Außentemperatur | `temp` |
| `sensor.kraichtal_wetter_feels_like` | Gefühlt | `feels_like` |
| `sensor.kraichtal_wetter_dew_point` | Taupunkt | `dewpoint` |
| `sensor.kraichtal_wetter_humidity` | Luftfeuchtigkeit | `humidity` |
| `sensor.kraichtal_wetter_pressure` | Luftdruck | `pressure` |
| `sensor.kraichtal_wetter_wind_speed` | Windgeschwindigkeit | `wind` |
| `sensor.kraichtal_wetter_wind_direction` | Windrichtung | `wind_dir` |
| `sensor.kraichtal_wetter_max_gust` | Böen max | `gust_max` |
| `sensor.kraichtal_wetter_solar_irradiance` | Solarstrahlung | `solar` |
| `sensor.kraichtal_wetter_precipitation` | Station heute Niederschlag | `rain` |
| `sensor.kraichtal_wetter_max_temperature_today` | Prognose Resttag Tmax | `tmax_today` |
| `sensor.kraichtal_wetter_min_temperature_today` | Prognose Resttag Tmin | `tmin_today` |
| `sensor.kraichtal_wetter_precipitation_today` | Prognose Resttag Niederschlag | `rain_today` |
| `sensor.kraichtal_wetter_warnings` | Warnungen | `warnings` |
| `sensor.kraichtal_wetter_observation_date` | Beobachtungsdatum | `obs_date` |
| `sensor.kraichtal_wetter_observation_time` | Beobachtungszeit | `obs_time` |
| `sensor.kraichtal_wetter_realtime_data` | Echtzeitdaten | `realtime` |
| `sensor.kraichtal_wetter_station_max_temperature_today` | Station heute Tmax | `station_today.tmax` |
| `sensor.kraichtal_wetter_station_min_temperature_today` | Station heute Tmin | `station_today.tmin` |
| `sensor.kraichtal_wetter_station_max_gust_today` | Station heute Böe | `station_today.gust` |
| `sensor.kraichtal_wetter_station_max_pressure_today` | Station heute Luftdruck max | `station_today.press_max` |
| `sensor.kraichtal_wetter_station_min_pressure_today` | Station heute Luftdruck min | `station_today.press_min` |
| `sensor.kraichtal_wetter_api_status` | API-Status (Diagnose) | – |

**Gemessen oder vorhergesagt?** Alles mit **„Station heute“** hat die Station tatsächlich gemessen — für „so viel hat es heute geregnet" ist `sensor.kraichtal_wetter_precipitation` der richtige Sensor. Die drei Sensoren **„Prognose Resttag“** sind dagegen Vorhersagen für die *verbleibenden* Stunden des Tages: Sie werden zum Abend hin kleiner und zeigen spät abends kaum mehr als die nächste Stunde. Die Vorhersage für den ganzen Tag steht in der Wetter-Entität.

Der **API-Status** ist als Diagnose-Entität eingestuft und steht bei einem erfolgreichen Abruf auf `ok`. Schlägt ein Abruf fehl, zeigt er stattdessen den Grund — etwa den Klartext der API oder die Bedeutung des HTTP-Status. Er bleibt dabei bewusst verfügbar, während die übrigen Entitäten auf „nicht verfügbar" gehen: Genau dann ist die Ursache interessant. Zu finden unter `Einstellungen → Geräte & Dienste → Kraichtal Wetter → Gerät`.

> **Upgrade auf 0.7.0:** Die Entity-IDs bleiben gleich, aber gemessener und vorhergesagter Niederschlag wurden bis dahin verwechselt. Wer `sensor.kraichtal_wetter_precipitation_today` als „Regen heute" in Automationen nutzt (etwa für die Bewässerung), hat mit einer Prognose gearbeitet und sollte auf `sensor.kraichtal_wetter_precipitation` wechseln. Unter `Entwicklerwerkzeuge → Statistik` meldet Home Assistant für die drei Prognose-Sensoren einmalig, dass sie keine Statistikklasse mehr haben — die alten Daten dort bitte löschen, sie sind nicht aussagekräftig. Details im [Changelog](CHANGELOG.md).

> **Upgrade von 0.4.x:** In 0.5.0 wurden die Entity-IDs von den deutschen Namen (`sensor.kraichtal_wetter_boen_max`) auf sprachunabhängige englische umgestellt. Die Integration benennt bestehende Entitäten beim ersten Start automatisch um, sodass die Recorder-Historie erhalten bleibt. Eigene Dashboards und Automationen müssen dagegen von Hand angepasst werden — Home Assistant schreibt Verweise dort nicht mit um.

## Lovelace Beispiele

### Übersicht

```yaml
type: vertical-stack
cards:
  - type: weather-forecast
    entity: weather.kraichtal_wetter

  - type: entities
    title: Kraichtal Wetter – Aktuelle Werte
    show_header_toggle: false
    entities:
      - sensor.kraichtal_wetter_outdoor_temperature
      - sensor.kraichtal_wetter_feels_like
      - sensor.kraichtal_wetter_humidity
      - sensor.kraichtal_wetter_pressure
      - sensor.kraichtal_wetter_wind_speed
      - sensor.kraichtal_wetter_warnings

  - type: entities
    title: Kraichtal Wetter – Heute gemessen
    show_header_toggle: false
    entities:
      - sensor.kraichtal_wetter_station_max_temperature_today
      - sensor.kraichtal_wetter_station_min_temperature_today
      - sensor.kraichtal_wetter_precipitation
```

### Verlauf

```yaml
type: history-graph
title: Verlauf Temperatur & Luftfeuchte
entities:
  - sensor.kraichtal_wetter_outdoor_temperature
  - sensor.kraichtal_wetter_humidity
hours_to_show: 24
```

## Hinweise

- Die Integration erscheint in Home Assistant als `Kraichtal Wetter`.
- Nutzer geben nur einen API-Key ein; die API-URL ist fest in der Integration hinterlegt.
- Alle Entitäten werden als Teil desselben Geräts in der Integrationen-Ansicht angezeigt.
- Der API-Key kann jederzeit über Einstellungen → Geräte & Dienste → Kraichtal Wetter → Konfiguration geändert werden.
- Das Abfrageintervall kann über die Optionen (Drei-Punkte-Menü → Optionen) angepasst werden — **mindestens 300 Sekunden**. Die API hält ihre Antwort serverseitig fünf Minuten vor; häufigere Abfragen liefern dieselben Daten und belasten nur den Betreiber. Ein niedrigerer Wert wird abgelehnt, ein früher gespeicherter beim Start auf 300 Sekunden angehoben.
- **Nicht jede Wetterlage, die Home Assistant kennt, kann diese Station liefern.**
  Hagel und Sturm stecken bei der Quelle in den Warn- bzw. Windfeldern und nicht
  in der Wetterlage, Schneeregen und gefrierender Regen laufen dort unter
  Schneefall, und ein Gewitter ohne Niederschlag gibt es nicht. Die Zustände
  `hail`, `windy`, `windy-variant`, `snowy-rainy`, `lightning` und `exceptional`
  treten deshalb nie auf — das ist eine Eigenschaft der Datenquelle, kein Fehler
  der Integration. Nebel (`fog`) wird dagegen unterstützt.

## Repository

Dieses Repository enthält die Custom Integration unter `custom_components/kraichtal_wetter` sowie die Dokumentation und das Changelog für die Integration.

## Lizenz

[MIT](LICENSE)
