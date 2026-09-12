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
- Was die Integration davon nutzt, bewusst nicht nutzt und was die API für Erweiterungen hergibt: [`docs/API.md`](docs/API.md).
- Reihenfolge, Stand und Entscheidungen der geplanten Arbeiten: [`Plan.md`](Plan.md).

Das ist keine Formalie, sondern zweimal aus Schaden gelernt:

- Die Icon-Zuordnung wurde einmal aus den SVG-Zeichnungen des Dashboards abgeleitet. Das ergab plausible, aber falsche Werte — `storm` zeichnet nur einen Blitz, ist laut Doku aber das *schwache Gewitter* und führt Regen. Aus einem Symbol lässt sich die Semantik nicht ablesen.
- `rain_today` klingt nach Tagessumme und wurde bis 0.6.x als `total_increasing` geführt. Laut Doku ist es eine *Prognose*; die gemessene Tagessumme heißt schlicht `rain`. Jede Korrektur der Prognose nach unten galt als Zählerreset, die Langzeitstatistik war damit wertlos. Aus einem Feldnamen lässt sich die Semantik genauso wenig ablesen.

Wenn eine neue Funktion eine bisher ungenutzte Sektion braucht, gehört sie in `REQUESTED_SECTIONS` (`coordinator.py`) — ohne das kommt sie schlicht nicht in der Antwort an.

## Wichtige Konventionen

- **API-Key-Feldname**: `key` (nicht `api_key`). Rückwärtskompatibel: `async_setup_entry` in `__init__.py` akzeptiert auch `api_key` / `apikey` aus alten Installationen.
- **API-URL** ist in `const.py` hardcodiert — Nutzer geben nur den Key an.
- **Entity-Namen kommen aus `translations/`**, nicht aus `name=` im Code: `SENSOR_TYPES` setzt `translation_key`, die Namen stehen unter `entity.sensor.<translation_key>.name`.
- **Entity-IDs leiten sich vom *englischen* Namen ab** (HA generiert Object-IDs bewusst sprachunabhängig aus `en.json`): `"Max gust"` → `sensor.kraichtal_wetter_max_gust`. Die Namen in `translations/en.json` sind damit **öffentliche API** — sie zu ändern verschiebt die Entity-IDs für Neuinstallationen. `de.json` beeinflusst nur die Anzeige. Vollständige Zuordnung in `README.md`.
- **Entity-ID-Migration**: `_SENSOR_ENTITY_ID_MIGRATION` in `__init__.py` benennt die vor 0.5.0 aus deutschen Namen erzeugten IDs um. Läuft idempotent bei jedem Setup vor `async_forward_entry_setups` und lässt selbst umbenannte Entitäten in Ruhe. Beim Hinzufügen eines Sensors ist hier nichts zu tun; beim Umbenennen eines englischen Namens schon.
- **Messung vs. Prognose**: `rain` ist die *gemessene* Tagessumme (`total_increasing`). `rain_today`, `tmax_today` und `tmin_today` sind *Prognosen* für die restlichen Stunden des Tages und tragen deshalb keine State-Class — Home Assistant schließt Vorhersagen ausdrücklich von `measurement` aus. Im Deutschen heißen gemessene Tageswerte „Station heute …", Prognosen „Prognose Resttag …". Details in `docs/API.md`.
- **Attribute**: Weitere API-Felder hängen über `attributes` in `KraichtalWetterSensorEntityDescription` am Sensor — Paare aus Attributname und API-Feld (Dot-Notation wie bei `key`). `None` wird ausgelassen. Name und Werte werden unter `entity.sensor.<translation_key>.state_attributes` übersetzt, in allen drei JSON-Dateien.
- **Sensoren** nutzen Dot-Notation in `sensor.py` um verschachtelte API-Felder aufzulösen (z.B. `station_today.tmax` → `data["current"]["station_today"]["tmax"]`).
- **Forecast-Datum** wird aus `meta.generated` + Tages-Index berechnet (API liefert kein `date` pro Tag); Umrechnung über `dt_util.start_of_local_day()` pro Tag, damit DST-Wechsel korrekt bleiben.
- **Forecast-Caching**: `async_forecast_daily()` und `async_forecast_hourly()` cachen, `_handle_coordinator_update()` invalidiert beide. Nicht `async_update()` verwenden — `CoordinatorEntity` setzt `should_poll = False`, die Methode würde nie aufgerufen. Dort steht auch der Push an `async_update_listeners()`: Ohne ihn bleibt die Vorhersage in einem offenen Dashboard auf dem Stand vom Öffnen, denn der geschriebene Zustand erreicht die Forecast-Abonnenten nicht.
- **Stundenvorhersage**: Die Einträge in `hours` tragen nur eine Beschriftung („Jetzt", „15:00"), kein Datum. `_hourly_datetimes()` verankert die Reihe an der ersten beschrifteten Stunde und zählt in UTC weiter (Zeitumstellung), `API_TIME_ZONE` ist fest `Europe/Berlin` — die API rechnet in dieser Zone, unabhängig von der Zeitzone der Instanz. Herleitung in `docs/API.md`.
- **ICON_MAP** in `weather.py` übersetzt API-Icon-Namen in HA-Wetterbedingungen. Nur Werte aus `ATTR_CONDITION_*` sind gültig; unbekannte Icons ergeben bewusst `None` statt einer falschen Bedingung. Die Tabelle deckt alle 19 dokumentierten Codes ab und ist gegen die Doku bestätigt — **nicht aus Icons neu herleiten** (siehe oben).
- **Auth-Fehler**: 401/403 → `ConfigEntryAuthFailed` (startet Reauth), alles andere → `UpdateFailed`. Setzt voraus, dass der Coordinator mit `config_entry=entry` erzeugt wird.
- **Sektionen**: `REQUESTED_SECTIONS` in `coordinator.py` grenzt den Abruf auf `current,days,hours` ein — ohne `section` liefert die API alle elf. `meta` kommt immer mit und darf nicht angefordert werden.
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

### Changelog mit Icons

Seit 0.8.0 tragen die Abschnittsüberschriften ein festes Icon, jeder Eintrag zusätzlich ein thematisches. Ältere Einträge bleiben, wie sie sind. Die Extraktion in `release.yml` sucht nur `## [Version]` und ist davon nicht betroffen.

| Abschnitt | Icon |
| --- | --- |
| Hinzugefügt | ✨ |
| Behoben | 🐛 |
| Geändert | 🔧 |
| Entfernt | 🗑️ |
| Sicherheit | 🔒 |
| Nach dem Update zu tun | ⚠️ |
| Getestet / Bestätigt | ✅ |
| Bekannt | ℹ️ |

Thematisch zum Beispiel: 🌡️ Temperatur · 🌧️ Niederschlag · 💨 Wind · 🌬️ Böen · 🚨 DWD-Warnungen · 🕒 Zeit · 🌐 Übersetzung · 📝 Doku · 🧪 Tests.

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
├── sensor.py            # 23 Messwert-Sensoren + Diagnose-Sensor API-Status
├── weather.py           # WeatherEntity + Forecast
├── strings.json         # Quelle der UI-Texte (nicht zur Laufzeit geladen)
├── translations/        # de.json + en.json — das lädt HA tatsächlich
└── brand/               # 4 Brand-Icons (icon + @2x + dark_*), lokale Auslieferung seit HA 2026.3
hacs.json                # HACS-Metadaten
docs/API.md              # Was die Integration von der API nutzt — und was die API sonst hergibt
Plan.md                  # Umsetzungsplan: Reihenfolge, Stand, Entscheidungen
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

### Das Icon fehlt in HACS — bekannt, nicht unser Fehler

**Nicht erneut untersuchen und keinen PR gegen `home-assistant/brands` öffnen.** Beides wurde bereits erledigt; hier das Ergebnis:

- Unter *Einstellungen → Geräte & Dienste* erscheint das Icon korrekt. Home Assistant liefert seit 2026.3 lokale Brand-Bilder über `/api/brands/integration/{domain}/{image}` aus, lokale Dateien haben Vorrang vor dem CDN ([Ankündigung](https://developers.home-assistant.io/blog/2026/02/24/brands-proxy-api)). Der `brand/`-Ordner ist damit der aktuelle und richtige Mechanismus.
- **In der HACS-Oberfläche fehlt es trotzdem.** HACS nutzt diesen Endpunkt nirgends: Im gesamten Python-Code gibt es genau eine Icon-URL, fest verdrahtet auf `https://brands.home-assistant.io/_/{domain}/icon.png` (`update.py`, `entity_picture`). Das CDN kennt unsere Domain nicht und liefert einen Platzhalter „icon not available".
- **Ein Brands-PR behebt das nicht.** `home-assistant/brands` nimmt seit 2026.3 keine Icons für Custom-Integrationen mehr an — unser PR dort ([#10964](https://github.com/home-assistant/brands/pull/10964), 13.08.2026) wurde eine Minute nach dem Öffnen automatisch geschlossen.
- **Ein Issue anzulegen ist ebenfalls überflüssig.** Vier offene Meldungen decken den Fall bereits ab: hacs/integration [#5171](https://github.com/hacs/integration/issues/5171), [#5179](https://github.com/hacs/integration/issues/5179), [#5223](https://github.com/hacs/integration/issues/5223), [#5402](https://github.com/hacs/integration/issues/5402) (letzteres mit Label `issue:frontend`). Alle seit März bzw. Juli 2026 offen, bislang ohne Reaktion der Maintainer.

Fazit: Am Repo ist nichts zu tun. Sobald HACS die lokale Brands-API übernimmt, erscheint das Icon ohne Zutun. Auch die Aufnahme in den HACS-Standardkatalog ändert daran nichts — Icon-Auslieferung und Katalogliste sind getrennte Systeme.

Dokumentation nur im Root-`README.md` pflegen; im Integrationsordner liegt bewusst keine zweite README mehr.
