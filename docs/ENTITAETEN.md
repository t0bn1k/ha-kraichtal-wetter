# Entitäten im Detail

Alle Entitäten der Integration, ihre Attribute und was die Datenquelle grundsätzlich nicht liefert. Die Kurzfassung steht im [README](https://github.com/t0bn1k/ha-kraichtal-wetter#readme).

## Übersicht

Anzeigenamen und Entity-IDs folgen der eingestellten Home-Assistant-Sprache; die Tabelle zeigt eine deutsche Instanz. **Wie die IDs genau aufgebaut sind, bestimmt Home Assistant, nicht die Integration** — je nach dem dort eingestellten Format kann der Bereich vorangestellt sein, etwa `sensor.garten_kraichtal_wetter_station_heute_wind_max`. Die tatsächlichen IDs stehen unter `Einstellungen → Geräte & Dienste → Kraichtal Wetter → Gerät`.

| Entität | Anzeige (Deutsch) | API-Feld |
| --- | --- | --- |
| `weather.kraichtal_wetter` | Kraichtal Wetter | – |
| `sensor.kraichtal_wetter_aussentemperatur` | Außentemperatur | `temp` |
| `sensor.kraichtal_wetter_gefuhlt` | Gefühlt | `feels_like` |
| `sensor.kraichtal_wetter_taupunkt` | Taupunkt | `dewpoint` |
| `sensor.kraichtal_wetter_luftfeuchtigkeit` | Luftfeuchtigkeit | `humidity` |
| `sensor.kraichtal_wetter_luftdruck` | Luftdruck | `pressure` |
| `sensor.kraichtal_wetter_windgeschwindigkeit` | Windgeschwindigkeit | `wind` |
| `sensor.kraichtal_wetter_windrichtung` | Windrichtung | `wind_dir` |
| `sensor.kraichtal_wetter_boen_max` | Böen max | `gust_max` |
| `sensor.kraichtal_wetter_solarstrahlung` | Solarstrahlung | `solar` |
| `sensor.kraichtal_wetter_station_heute_niederschlag` | Station heute Niederschlag | `rain` |
| `sensor.kraichtal_wetter_prognose_resttag_tmax` | Prognose Resttag Tmax | `tmax_today` |
| `sensor.kraichtal_wetter_prognose_resttag_tmin` | Prognose Resttag Tmin | `tmin_today` |
| `sensor.kraichtal_wetter_prognose_resttag_niederschlag` | Prognose Resttag Niederschlag | `rain_today` |
| `sensor.kraichtal_wetter_prognose_heute_regenwahrscheinlichkeit` | Prognose heute Regenwahrscheinlichkeit | `days[0].pop` |
| `sensor.kraichtal_wetter_prognose_morgen_tmax` | Prognose morgen Tmax | `days[1].tmax` |
| `sensor.kraichtal_wetter_prognose_morgen_tmin` | Prognose morgen Tmin | `days[1].tmin` |
| `sensor.kraichtal_wetter_prognose_morgen_niederschlag` | Prognose morgen Niederschlag | `days[1].rain` |
| `sensor.kraichtal_wetter_prognose_morgen_regenwahrscheinlichkeit` | Prognose morgen Regenwahrscheinlichkeit | `days[1].pop` |
| `sensor.kraichtal_wetter_warnungen` | Warnungen | `warnings` |
| `sensor.kraichtal_wetter_beobachtungsdatum` | Beobachtungsdatum | `obs_date` |
| `sensor.kraichtal_wetter_beobachtungszeit` | Beobachtungszeit | `obs_time` |
| `sensor.kraichtal_wetter_echtzeitdaten` | Echtzeitdaten | `realtime` |
| `sensor.kraichtal_wetter_station_heute_tmax` | Station heute Tmax | `station_today.tmax` |
| `sensor.kraichtal_wetter_station_heute_tmin` | Station heute Tmin | `station_today.tmin` |
| `sensor.kraichtal_wetter_station_heute_boe` | Station heute Böe | `station_today.gust` |
| `sensor.kraichtal_wetter_station_heute_wind_max` | Station heute Wind max | `station_today.wind_max` |
| `sensor.kraichtal_wetter_station_heute_luftdruck_max` | Station heute Luftdruck max | `station_today.press_max` |
| `sensor.kraichtal_wetter_station_heute_luftdruck_min` | Station heute Luftdruck min | `station_today.press_min` |
| `sensor.kraichtal_wetter_api_status` | API-Status (Diagnose) | – |

Was die Felder laut API bedeuten und was die API darüber hinaus anbietet, steht in [`API.md`](https://github.com/t0bn1k/ha-kraichtal-wetter/blob/main/docs/API.md).

## Gemessen oder vorhergesagt?

Alles mit **„Station heute“** hat die Station tatsächlich gemessen — für „so viel hat es heute geregnet“ ist `sensor.kraichtal_wetter_station_heute_niederschlag` der richtige Sensor.

Die drei Sensoren **„Prognose Resttag“** sind dagegen Vorhersagen für die *verbleibenden* Stunden des Tages: Sie werden zum Abend hin kleiner und zeigen spät abends kaum mehr als die nächste Stunde.

**„Prognose heute“ und „Prognose morgen“** stammen aus der Tagesvorhersage und gelten für den ganzen Kalendertag. „Prognose morgen Tmin“ schließt also die Nacht nach Mitternacht ein — das ist der Wert für eine Frostabfrage, etwa `{{ states('sensor.kraichtal_wetter_prognose_morgen_tmin') | float(99) < 2 }}`.

Prognosen führen keine Langzeitstatistik; Home Assistant schließt Vorhersagen davon ausdrücklich aus.

## Zusätzliche Attribute

| Sensor | Attribut | Inhalt |
| --- | --- | --- |
| Außentemperatur | `source` | `live` = gemessen, `forecast` = mangels Messwert aus der Prognose |
| Station heute Tmax, Tmin, Böe | `time` | Uhrzeit des Extremwerts, z. B. `15:53` |
| Station heute Böe | `beaufort` | Windstärke |
| Prognose heute/morgen … | `confidence` | Wie einig sich die Wettermodelle für diesen Tag sind, in Prozent („Einigkeit der Modelle“) |

In der Oberfläche erscheinen die Attribute übersetzt („Quelle“, „Uhrzeit“); in Templates gilt der englische Name, etwa `{{ state_attr('sensor.kraichtal_wetter_station_heute_tmax', 'time') }}`.

## API-Status

Der **API-Status** ist als Diagnose-Entität eingestuft und steht bei einem erfolgreichen Abruf auf `ok`. Schlägt ein Abruf fehl, zeigt er stattdessen den Grund — etwa den Klartext der API oder die Bedeutung des HTTP-Status. Er bleibt dabei bewusst verfügbar, während die übrigen Entitäten auf „nicht verfügbar“ gehen: Genau dann ist die Ursache interessant.

## Abfrageintervall und API-Key

- Das Abfrageintervall lässt sich über `⋯ → Optionen` ändern, **mindestens 300 Sekunden**. Die API hält ihre Antwort serverseitig fünf Minuten vor; häufigere Abfragen liefern dieselben Daten und belasten nur den Betreiber. Ein niedrigerer Wert wird abgelehnt, ein früher gespeicherter beim Start auf 300 Sekunden angehoben. Ein geänderter Wert gilt sofort, ohne Neustart.
- Der API-Key wird bei der Einrichtung gegen die API geprüft; ein abgelehnter Key wird direkt am Formular gemeldet. Lehnt die API einen hinterlegten Key später ab, fragt Home Assistant unter `Einstellungen → Geräte & Dienste` nach einem neuen — auch der wird vor dem Speichern geprüft.

## Was die Datenquelle nicht liefert

- **Warnungen im Detail.** Der Sensor *Warnungen* zeigt nur, **wie viele** DWD-Warnungen gerade gelten. Für Text, Verhaltenshinweise, Beginn und Ende ist die in Home Assistant mitgelieferte Integration [Deutscher Wetterdienst (DWD) Weather Warnings](https://www.home-assistant.io/integrations/dwd_weather_warnings/) die bessere Wahl.
- **Einige Wetterlagen.** Hagel und Sturm stecken bei der Quelle in den Warn- bzw. Windfeldern und nicht in der Wetterlage, Schneeregen und gefrierender Regen laufen dort unter Schneefall, und ein Gewitter ohne Niederschlag gibt es nicht. Die Zustände `hail`, `windy`, `windy-variant`, `snowy-rainy`, `lightning` und `exceptional` treten deshalb nie auf — das ist eine Eigenschaft der Datenquelle, kein Fehler der Integration. Nebel (`fog`) wird unterstützt.
- **Regenmenge und Windrichtung je Stunde.** Die Stundenvorhersage enthält Temperatur, Regenwahrscheinlichkeit, Wind und Wetterlage.
