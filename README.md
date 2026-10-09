# Kraichtal Wetter

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg?style=for-the-badge)](https://github.com/hacs/integration)
[![Release](https://img.shields.io/github/v/release/t0bn1k/ha-kraichtal-wetter?style=for-the-badge)](https://github.com/t0bn1k/ha-kraichtal-wetter/releases)
[![Tests](https://img.shields.io/github/actions/workflow/status/t0bn1k/ha-kraichtal-wetter/tests.yml?style=for-the-badge&label=tests)](https://github.com/t0bn1k/ha-kraichtal-wetter/actions/workflows/tests.yml)
<!-- Installationen-Badge: erst nach Aufnahme in den HACS-Standardkatalog einschalten, vorher zeigt er nur "no result"
[![Installationen](https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fanalytics.home-assistant.io%2Fcustom_integrations.json&query=%24.kraichtal_wetter.total&label=Installationen&color=41BDF5&style=for-the-badge)](https://analytics.home-assistant.io/)
-->

Bringt die Wetterstation von [kraichtal-wetter.de](https://kraichtal-wetter.de) in dein Home Assistant: aktuelle Messwerte, die Tageswerte der Station und eine Vorhersage für die nächsten Stunden und Tage.

## Was die Integration kann

- **Aktuelle Messwerte:** Temperatur, gefühlte Temperatur, Taupunkt, Luftfeuchtigkeit, Luftdruck, Wind, Böen und Sonneneinstrahlung.
- **Tageswerte der Station:** Höchst- und Tiefstwert mit Uhrzeit, gefallener Regen, stärkste Böe, Luftdruck-Spanne.
- **Wettervorhersage für acht Tage und zwölf Stunden**, direkt nutzbar in der Wetterkarte von Home Assistant.
- **Vorhersage für heute und morgen als eigene Sensoren** für Automationen wie Frostschutz oder Bewässerung, ganz ohne Template.
- **Anzahl der aktuellen DWD-Warnungen.**
- **Einrichtung komplett in der Oberfläche:** Du brauchst nur einen API-Key, die Daten aktualisieren sich alle fünf Minuten.

Alle Sensoren mit Entity-IDs und Attributen: [Entitäten im Detail](https://github.com/t0bn1k/ha-kraichtal-wetter/blob/main/docs/ENTITAETEN.md).

## API-Key besorgen

Die Integration braucht einen eigenen, **kostenlosen** API-Key. Du beantragst ihn über ein kurzes Formular:

**→ [kraichtal-wetter.de/dashboard/apply.php](https://kraichtal-wetter.de/dashboard/apply.php)**

Dort gibst du einen Namen oder Verwendungszweck an (z. B. `Home-Assistant Müller`) und eine E-Mail-Adresse für Rückfragen und löst eine kleine Rechenaufgabe.

## Installation

1. **In HACS hinzufügen:** Klick auf den Button und bestätige mit „Hinzufügen“.

   [![In HACS öffnen](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=t0bn1k&repository=ha-kraichtal-wetter&category=integration)

   <sub>Ohne Button: in HACS über `⋯ → Benutzerdefinierte Repositorys` die URL `https://github.com/t0bn1k/ha-kraichtal-wetter` mit Typ „Integration“ eintragen.</sub>

2. **Herunterladen** und Home Assistant neu starten.

3. **Integration einrichten** und den API-Key eingeben:

   [![Integration einrichten](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=kraichtal_wetter)

   <sub>Oder über `Einstellungen → Geräte & Dienste → Integration hinzufügen → Kraichtal Wetter`.</sub>

Fertig: Unter `Einstellungen → Geräte & Dienste` erscheint das Gerät **Kraichtal Wetter** mit der Wetter-Entität und allen Sensoren.

<details>
<summary>Ohne HACS installieren</summary>

1. Den Ordner `custom_components/kraichtal_wetter` aus diesem Repository in das `custom_components`-Verzeichnis deiner Home-Assistant-Konfiguration kopieren.
2. Home Assistant neu starten.
3. Weiter mit Schritt 3 oben.

</details>

## Beispielkarten

So sieht es auf dem Dashboard aus. Den YAML-Code fügst du über `Karte hinzufügen → Manuell` ein.

<img src="https://raw.githubusercontent.com/t0bn1k/ha-kraichtal-wetter/main/docs/images/karte-wetter.png" width="440" alt="Wetterkarte: aktuelle Lage und Vorhersage für sieben Tage">

<details>
<summary>YAML: Wetter und Tagesvorhersage</summary>

```yaml
type: weather-forecast
entity: weather.kraichtal_wetter
name: Kraichtal
forecast_type: daily
secondary_info_attribute: apparent_temperature
```

</details>

<img src="https://raw.githubusercontent.com/t0bn1k/ha-kraichtal-wetter/main/docs/images/karte-stunden.png" width="440" alt="Stundenvorhersage">

<details>
<summary>YAML: Stundenvorhersage</summary>

```yaml
type: weather-forecast
entity: weather.kraichtal_wetter
forecast_type: hourly
show_current: false
```

</details>

<img src="https://raw.githubusercontent.com/t0bn1k/ha-kraichtal-wetter/main/docs/images/karte-aktuell.png" width="440" alt="Karte mit den aktuellen Messwerten">

<details>
<summary>YAML: Aktuelle Werte</summary>

```yaml
type: entities
title: Aktuelle Werte
entities:
  - entity: sensor.kraichtal_wetter_aussentemperatur
    name: Außentemperatur
  - entity: sensor.kraichtal_wetter_gefuhlt
    name: Gefühlt
  - entity: sensor.kraichtal_wetter_luftfeuchtigkeit
    name: Luftfeuchtigkeit
  - entity: sensor.kraichtal_wetter_luftdruck
    name: Luftdruck
  - entity: sensor.kraichtal_wetter_windgeschwindigkeit
    name: Wind
  - entity: sensor.kraichtal_wetter_boen_max
    name: Böen max
  - entity: sensor.kraichtal_wetter_solarstrahlung
    name: Solarstrahlung
```

</details>

<img src="https://raw.githubusercontent.com/t0bn1k/ha-kraichtal-wetter/main/docs/images/karte-heute-morgen.png" width="440" alt="Karte mit den gemessenen Werten von heute und der Vorhersage für morgen">

<details>
<summary>YAML: Heute und morgen</summary>

```yaml
type: entities
title: Heute und morgen
entities:
  - type: section
    label: Heute gemessen
  - entity: sensor.kraichtal_wetter_station_heute_tmax
    name: Höchstwert
  - entity: sensor.kraichtal_wetter_station_heute_tmin
    name: Tiefstwert
  - entity: sensor.kraichtal_wetter_station_heute_niederschlag
    name: Niederschlag
  - type: section
    label: Morgen erwartet
  - entity: sensor.kraichtal_wetter_prognose_morgen_tmax
    name: Höchstwert
  - entity: sensor.kraichtal_wetter_prognose_morgen_tmin
    name: Tiefstwert
  - entity: sensor.kraichtal_wetter_prognose_morgen_regenwahrscheinlichkeit
    name: Regenwahrscheinlichkeit
```

</details>

Die Bilder zeigen Beispieldaten. Die Entity-IDs gelten für eine deutschsprachige Instanz; stellt dein Home Assistant den Bereich voran (z. B. `sensor.garten_kraichtal_wetter_…`), passe sie entsprechend an. Ein komplettes Dashboard mit allen Sensoren liegt unter [`lovelace/kraichtal_wetter_overview.yaml`](https://github.com/t0bn1k/ha-kraichtal-wetter/blob/main/lovelace/kraichtal_wetter_overview.yaml).

## Gut zu wissen

- **Gemessen oder vorhergesagt?** Sensoren mit **„Station heute“** zeigen, was die Station tatsächlich gemessen hat. Sensoren mit **„Prognose“** sind Vorhersagen. Für „so viel hat es heute geregnet“ ist also *Station heute Niederschlag* der richtige Sensor.
- **DWD-Warnungen im Detail** (Text, Beginn, Ende) liefert die in Home Assistant enthaltene Integration [DWD Weather Warnings](https://www.home-assistant.io/integrations/dwd_weather_warnings/); hier gibt es nur die Anzahl.
- **Abfrageintervall:** über `⋯ → Optionen` einstellbar, mindestens fünf Minuten. Häufiger lohnt nicht, denn die API liefert ohnehin nur alle fünf Minuten neue Daten.
- **Neuer API-Key:** Lehnt die API deinen Key ab, fragt Home Assistant unter `Einstellungen → Geräte & Dienste` von selbst nach einem neuen.

## Hilfe und Fehler melden

Wenn keine Werte ankommen, sieh zuerst auf den Sensor **API-Status** am Gerät: Er nennt den Grund, etwa einen ungültigen Key oder eine nicht erreichbare API.

Für einen Fehlerbericht lade unter `Einstellungen → Geräte & Dienste → Kraichtal Wetter → ⋯ → Diagnose herunterladen` die Diagnosedatei herunter und hänge sie an ein [Issue](https://github.com/t0bn1k/ha-kraichtal-wetter/issues). **Dein API-Key wird darin automatisch entfernt.**

Was sich in welcher Version geändert hat, steht im [Changelog](https://github.com/t0bn1k/ha-kraichtal-wetter/blob/main/CHANGELOG.md).

---

[MIT-Lizenz](https://github.com/t0bn1k/ha-kraichtal-wetter/blob/main/LICENSE) · Entwickelt mit [Claude Code](https://claude.com/claude-code) · Mitmachen: [Hinweise für Entwickler](https://github.com/t0bn1k/ha-kraichtal-wetter/blob/main/AGENTS.md#tests)
