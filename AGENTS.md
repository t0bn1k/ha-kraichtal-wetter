# Kraichtal Wetter — HACS Custom Component

## Repo-Übersicht

Home-Assistant-Custom-Integration für die Kraichtal-Wetter-API. Kein Build-System, keine Tests, keine Linter.

## Domain & Manifest

- Domain: `kraichtal_wetter` · HA-Minimum: `2026.3` · `iot_class: cloud_polling`
- Plattformen: `sensor`, `weather`
- Keine externen Abhängigkeiten (`requirements: []`)

## Die API ist die Referenz — vorab prüfen

**Bevor du etwas hinzufügst oder änderst, das API-Daten betrifft, prüfe es gegen die API-Dokumentation** — nicht gegen das Dashboard, den Augenschein eines Symbols oder eine Vermutung darüber, was ein Feld wohl bedeutet.

- Offizielle Doku: <https://kraichtal-wetter.de/dashboard/api-doku.html>
- Was die Integration davon nutzt, bewusst nicht nutzt und was vorgemerkt ist: [`docs/API.md`](docs/API.md) — dort steht auch der Backlog (`hours`, `alerts`, `temp_source`, ETag …).

Das ist keine Formalie, sondern aus Schaden gelernt: Die Icon-Zuordnung wurde einmal aus den SVG-Zeichnungen des Dashboards abgeleitet. Das ergab plausible, aber falsche Werte — `storm` zeichnet nur einen Blitz, ist laut Doku aber das *schwache Gewitter* und führt Regen. Aus einem Symbol lässt sich die Semantik nicht ablesen.

Wenn eine neue Funktion eine bisher ungenutzte Sektion braucht, gehört sie in `REQUESTED_SECTIONS` (`coordinator.py`) — ohne das kommt sie schlicht nicht in der Antwort an.

## Wichtige Konventionen

- **API-Key-Feldname**: `key` (nicht `api_key`). Rückwärtskompatibel: `async_setup_entry` in `__init__.py` akzeptiert auch `api_key` / `apikey` aus alten Installationen.
- **API-URL** ist in `const.py` hardcodiert — Nutzer geben nur den Key an.
- **Entity-Namen kommen aus `translations/`**, nicht aus `name=` im Code: `SENSOR_TYPES` setzt `translation_key`, die Namen stehen unter `entity.sensor.<translation_key>.name`.
- **Entity-IDs leiten sich vom *englischen* Namen ab** (HA generiert Object-IDs bewusst sprachunabhängig aus `en.json`): `"Max gust"` → `sensor.kraichtal_wetter_max_gust`. Die Namen in `translations/en.json` sind damit **öffentliche API** — sie zu ändern verschiebt die Entity-IDs für Neuinstallationen. `de.json` beeinflusst nur die Anzeige. Vollständige Zuordnung in `README.md`.
- **Entity-ID-Migration**: `_SENSOR_ENTITY_ID_MIGRATION` in `__init__.py` benennt die vor 0.5.0 aus deutschen Namen erzeugten IDs um. Läuft idempotent bei jedem Setup vor `async_forward_entry_setups` und lässt selbst umbenannte Entitäten in Ruhe. Beim Hinzufügen eines Sensors ist hier nichts zu tun; beim Umbenennen eines englischen Namens schon.
- **Sensoren** nutzen Dot-Notation in `sensor.py` um verschachtelte API-Felder aufzulösen (z.B. `station_today.tmax` → `data["current"]["station_today"]["tmax"]`).
- **Forecast-Datum** wird aus `meta.generated` + Tages-Index berechnet (API liefert kein `date` pro Tag); Umrechnung über `dt_util.start_of_local_day()` pro Tag, damit DST-Wechsel korrekt bleiben.
- **Forecast-Caching**: `async_forecast_daily()` cached, `_handle_coordinator_update()` invalidiert. Nicht `async_update()` verwenden — `CoordinatorEntity` setzt `should_poll = False`, die Methode würde nie aufgerufen.
- **ICON_MAP** in `weather.py` übersetzt API-Icon-Namen in HA-Wetterbedingungen. Nur Werte aus `ATTR_CONDITION_*` sind gültig; unbekannte Icons ergeben bewusst `None` statt einer falschen Bedingung. Die Tabelle deckt alle 19 dokumentierten Codes ab und ist gegen die Doku bestätigt — **nicht aus Icons neu herleiten** (siehe oben).
- **Auth-Fehler**: 401/403 → `ConfigEntryAuthFailed` (startet Reauth), alles andere → `UpdateFailed`. Setzt voraus, dass der Coordinator mit `config_entry=entry` erzeugt wird.
- **Sektionen**: `REQUESTED_SECTIONS` in `coordinator.py` grenzt den Abruf auf `current,days` ein — ohne `section` liefert die API alle elf. `meta` kommt immer mit und darf nicht angefordert werden.
- **Fehlertexte sichtbar machen**: Der Sensor **API-Status** (`EntityCategory.DIAGNOSTIC`) zeigt den letzten Fehler am Gerät. Er überschreibt `available` bewusst mit `True` — sonst wäre er genau dann nicht sichtbar, wenn er gebraucht wird.
- **API-Key gehört in den `X-API-Key`-Header, nie in die URL.** `aiohttp.ClientResponseError` bettet die Request-URL in seine String-Repräsentation ein — ein Key im Query-String erreicht darüber jedes Log. `_split_api_key()` in `coordinator.py` zieht einen in der URL konfigurierten Key heraus und bereinigt die URL; kein Codepfad darf ihn zurückschreiben. Zusätzlich als zweite Ebene: nur Status/`err.message` loggen, `from None` statt `from err`.
- **Auth-Semantik der API**: 401 = Key fehlt, 403 = Key ungültig (beides verifiziert). Beide in `AUTH_ERROR_STATUSES`.
- **`scan_interval`**: Default 300 s, **Minimum 300 s** (`MIN_SCAN_INTERVAL`). Die API cached serverseitig fünf Minuten — häufiger abzufragen liefert dieselbe Antwort. Beide Flows lehnen kleinere Werte ab; `async_setup_entry` hebt zusätzlich Bestandseinträge an, die das Schema nie wieder sieht.
- **hass.data**: `hass.data[DOMAIN][entry.entry_id]` speichert `{"coordinator", "client", "entry"}`.
- **UI-Sprache**: Deutsch. `strings.json` ist nur Quelle — zur Laufzeit lädt HA `translations/de.json` / `translations/en.json`; beide müssen mitgepflegt werden.

## CI / Release

- `.github/workflows/release.yml` — Tag `v*.*.*` erzeugt GitHub Release mit automatisch extrahiertem Changelog-Eintrag.
- `.github/workflows/validate.yml` — HACS-Action und Hassfest (Push, PR, nächtlich). Voraussetzung für die Aufnahme in den HACS-Standardkatalog.

Beim Release: `manifest.json` (`version`) und der CHANGELOG-Eintrag müssen zur Tag-Version passen, sonst greift die Changelog-Extraktion in `release.yml` nicht.

### Downloads-Badge

Bewusst **nicht** im README. Der übliche Badge liest `https://analytics.home-assistant.io/custom_integrations.json` unter `$.<domain>.total`; dort ist `kraichtal_wetter` nicht enthalten (die Liste erfasst nur Integrationen aus dem HACS-Standardkatalog mit Analytics-Opt-in der Nutzer), der Badge liefert also „no result". Ein GitHub-Downloadzähler hilft ebenfalls nicht, da die Releases keine Assets tragen und nur Assets gezählt werden. Nach Aufnahme in den Standardkatalog nutzbar:

```
[![Downloads](https://img.shields.io/badge/dynamic/json?url=https://analytics.home-assistant.io/custom_integrations.json&query=$.kraichtal_wetter.total&label=Downloads&color=41BDF5&style=for-the-badge)](https://analytics.home-assistant.io/)
```

## Verzeichnisstruktur

```
custom_components/kraichtal_wetter/
├── __init__.py          # async_setup_entry, Coordinator-Init
├── config_flow.py       # Config-Flow, Reauth, Options
├── const.py             # DOMAIN, Konstanten
├── coordinator.py       # KraichtalWetterClient (HTTP)
├── sensor.py            # 22 Messwert-Sensoren + Diagnose-Sensor API-Status
├── weather.py           # WeatherEntity + Forecast
├── strings.json         # Quelle der UI-Texte (nicht zur Laufzeit geladen)
├── translations/        # de.json + en.json — das lädt HA tatsächlich
└── brand/               # 8 Brand-Bilder (icon/logo + @2x + dark_*), lokale Auslieferung seit HA 2026.3
hacs.json                # HACS-Metadaten
docs/API.md              # Was die Integration von der API nutzt — und der Backlog
lovelace/                # Beispiel-Dashboards
```

## Stil (im Code)

- `from __future__ import annotations`
- `voluptuous` + `cv` für Schemata
- `urllib.parse` für URL-Bau (kein String-Concatenation)
- `CoordinatorEntity` + `SensorEntityDescription`-Pattern
- Einheiten/Geräteklassen über HA-Enums (`UnitOfTemperature`, `SensorDeviceClass`, …), nicht als String-Literale

## Brand-Bilder

`brand/` enthält bewusst nur die 4 Icons: `icon.png` (256×256), `icon@2x.png` (512×512) und die beiden `dark_`-Varianten — exakt die Maße, die home-assistant/brands vorschreibt. Ein Logo existiert nicht; laut Spezifikation wird dann `icon.png` ausgeliefert, Dark-Varianten fallen auf die hellen zurück.

Die früheren `logo*.png` waren quadratische Kopien der Icons in 512/1024 px und verletzten die Logo-Vorgabe (Querformat, kürzeste Seite 128–256 px bzw. 256–512 px). Ein echtes Logo müsste diesen Maßen entsprechen — keine Icon-Kopie.

Dokumentation nur im Root-`README.md` pflegen; im Integrationsordner liegt bewusst keine zweite README mehr.
