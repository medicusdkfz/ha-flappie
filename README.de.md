# Flappie für Home Assistant

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/v/release/medicusdkfz/ha-flappie)](https://github.com/medicusdkfz/ha-flappie/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

🇬🇧 [English version of this documentation](README.md)

Inoffizielle Home-Assistant-Integration für die [Flappie](https://flappiedoors.com)-Katzenklappe mit KI-Beuteerkennung. Klappe steuern, Ereignisfotos und -videos ansehen, Beute-Alarme erhalten und Langzeitstatistiken aufzeichnen — alles direkt in Home Assistant.

> **Hinweis:** Dieses Projekt ist nicht mit Flappie Technologies AG assoziiert. Es spricht dieselbe undokumentierte Cloud-API wie die offizielle App (`app.flappiedoors.com`); der Hersteller kann die API jederzeit ändern. Es gibt **keine lokale Schnittstelle** — die Klappe kommuniziert ausschließlich mit der Cloud, diese Integration ebenso.

Die API-Schicht ist eine Python-Portierung des reverse-engineerten npm-Pakets [`flappie-api`](https://github.com/ooswald/flappie-api) von Olivier Oswald — die rohe Endpunkt-Referenz steht in dessen [`CLOUD_API.md`](https://github.com/ooswald/flappie-api/blob/main/CLOUD_API.md).

---

## Funktionen

- **Einrichtung per UI** — Anmeldung mit dem Flappie-App-Konto, automatischer Token-Refresh, Reauth-Flow bei Passwortänderung
- **Türsteuerung** — Lock-Entität plus Türmodus-Select mit allen vier Policies (offen, geschlossen, nur Eingang, nur Ausgang)
- **Einstellungs-Schalter** — KI-Beuteerkennung, Beute-Zeitsperre (inkl. Dauer), physische Tasten, RFID-Flag
- **Ereignisfotos & -videos** — Bild-Entitäten für die letzten Ereignisse und eine Medienquelle, die Ereignisvideos direkt im HA-Medienbrowser abspielt (signierte URLs werden bei Bedarf frisch geholt, kein abgelaufener Link beim Abspielen)
- **Event-Entität** — feuert `activity`/`prey` bei jeder neuen Erkennung; ideal für Automatisierungen und Benachrichtigungen
- **Katzen als Geräte** — jedes Katzenprofil des Kontos wird ein eigenes HA-Gerät mit Gewichts-Sensor (Rasse, Geschlecht, Geburtstag als Attribute) und Profilbild
- **Langzeitstatistiken** — Aktivität und Beute pro Tag als HA-Langzeitstatistik, inklusive historischem Backfill (Beute seit Registrierung der Klappe!)
- **Übersetzt** — Deutsch, Englisch, Französisch und Italienisch

## Screenshots

*Beispiel-Dashboard (fertig anpassbares YAML in [`docs/dashboard.yaml`](docs/dashboard.yaml)):*

![Dashboard](docs/images/dashboard.png)

| Steuerung & Status | Katzen & Statistiken |
|---|---|
| ![Steuerung](docs/images/controls.png) | ![Statistiken](docs/images/stats.png) |

*Ereignisvideos im Medienbrowser und der Anmeldedialog:*

![Medienbrowser](docs/images/media-browser.png)

![Config Flow](docs/images/config-flow.png)

## Installation

### Via HACS (empfohlen)

1. HACS → Integrationen → ⋮ → **Benutzerdefinierte Repositories**
2. `https://github.com/medicusdkfz/ha-flappie` mit Kategorie **Integration** hinzufügen
3. **Flappie** installieren und Home Assistant neu starten

### Manuell

Den Ordner `custom_components/flappie` nach `<config>/custom_components/` kopieren und Home Assistant neu starten.

### Einrichtung

*Einstellungen → Geräte & Dienste → Integration hinzufügen → „Flappie"* und mit den Zugangsdaten der Flappie-App anmelden. Bei einer späteren Passwortänderung startet Home Assistant automatisch einen Reauth-Flow.

Benötigt Home Assistant **2024.12** oder neuer.

## Entitäten

Alle Entitäten werden pro Katzenklappe angelegt. `<name>` steht für den Gerätenamen (HA stellt in Entity-IDs ggf. den Bereichsnamen voran).

### Steuerung

| Entität | Typ | Beschreibung |
|---|---|---|
| `lock.<name>` | Lock | Verriegeln (`CLOSED`) / Entriegeln (`OPEN`). Attribute: rohe Door-Policy, Gerätestatus, Sperrgrund, `lock_until` |
| Türmodus | Select | Alle vier Policies: Offen, Geschlossen, Nur Eingang, Nur Ausgang |
| Beuteerkennung | Switch | KI-Beuteerkennung an/aus |
| Beute-Zeitsperre | Switch | Automatische Sperre nach Beutefund |
| Dauer Beutesperre | Number | Schieberegler in Minuten, 1–60 — der volle Bereich, den die Cloud annimmt (App-Standard: 15 Min.) |
| Tasten | Switch | Physische Tasten an der Klappe |
| RFID | Switch | Backend-Flag mit unbekannter Wirkung — laut Hersteller liest die Klappe **keine** Mikrochips (Zutrittskontrolle ist das kamerabasierte „Cat ID"). Standardmäßig ausgeblendet. |

### Sensoren

| Entität | Typ | Beschreibung |
|---|---|---|
| Türstatus | Sensor (Enum) | Tatsächlicher Zustand `locked`/`unlocked` mit `reason` und `lock_until` — kann vom eingestellten Modus abweichen, z. B. bei aktiver Beutesperre |
| Letztes Ereignis | Sensor (Zeitstempel) | Neueste Erkennung an der Klappe |
| Letztes Beute-Ereignis | Sensor (Zeitstempel) | Dauerhaft — stammt aus dem Cloud-Dashboard und überlebt den 7-Tage-Verfall der Ereignisliste (siehe [API-Hinweise](#api-hinweise--einschränkungen)) |
| Ereignisse heute | Sensor | Erkennungen seit Mitternacht (lokal) |
| Beute heute | Sensor | Beutefunde seit Mitternacht (lokal) |
| Blockierte Beute | Sensor | Kontoweiter Zähler aus dem Cloud-Dashboard |
| Signalqualität | Sensor (Diagnose) | WLAN-Indikator |
| Beutesperre aktiv | Binärsensor | Klappe ist gerade wegen erkannter Beute gesperrt |
| Zeitplan aktiv | Binärsensor | Ein Cloud-Zeitplan steuert die Klappe gerade |
| Problem | Binärsensor (Diagnose) | Betriebsstatus ≠ OK |

### Medien

| Entität | Typ | Beschreibung |
|---|---|---|
| Letztes Ereignisbild | Image | Schnappschuss des neuesten Ereignisses; holt immer eine frische signierte URL |
| Ereignis 1–4 | Image | Schnappschüsse der vier neuesten Ereignisse mit `bundle_id`, `created_at`, `is_prey` — ideal für Bildkarten im Dashboard |
| Klappen-Ereignis | Event | Feuert `activity` oder `prey` mit `bundle_id`, `created_at`, `has_video` |
| **Medienquelle** | — | *Medien → Flappie* listet die letzten Ereignisvideos (🐾 Aktivität / 🐭 Beute) mit Vorschaubildern, abspielbar im Browser oder auf Media-Playern |

### Katzen

Jedes Katzenprofil wird ein Gerät mit Sensoren für **Gewicht** (kg), **Geburtstag** (Datum), **Alter** (Jahre), **Rasse** und **Geschlecht** und, falls in der App ein Profilfoto gesetzt ist, einer **Profilbild**-Entität. In der App gepflegte Profildaten fließen automatisch ein.

### Gesundheits-Tracking

Jede Katze bekommt zusätzlich einen kleinen Gesundheits-Tracker für **Wurmkur**, **Flohbehandlung** und **Arztbesuch**. Diese Werte sind *nicht* Teil der Flappie-Cloud — sie werden lokal in Home Assistant gepflegt und überleben Neustarts.

| Entität | Typ | Beschreibung |
|---|---|---|
| Letzte Wurmkur / Flohbehandlung / Letzter Arztbesuch | Datum | Datum der letzten Behandlung setzen |
| Intervall Wurmkur / Flohbehandlung / Arztbesuch (Monate) | Number (Konfiguration) | Individuelles Intervall pro Katze (1–12 Monate, Slider); Standard: Wurmkur 3, Flöhe 1, Arzt 12 |
| Behandlungen: Katzen koppeln | Switch (Konfiguration, am Klappen-Gerät) | An: Eine Datums-/Intervall-Eingabe gilt für alle Katzen gleichzeitig |
| Behandlungen: Kombipräparat (Wurm & Floh) | Switch (Konfiguration, am Klappen-Gerät) | An: Wurmkur und Flohbehandlung werden gemeinsam gepflegt (Spot-on-Kombipräparate); kombinierbar mit *Katzen koppeln* |
| Nächste Wurmkur / Flohbehandlung / Nächster Arztbesuch | Sensor (Datum) | Berechnet: letzte Behandlung + Intervall |
| Wurmkur / Flohbehandlung / Arztbesuch fällig | Binärsensor | An, sobald der nächste Termin heute oder überschritten ist — ideal als Automatisierungs-Trigger |

Typischer Ablauf: Nach der Behandlung die *Letzte …*-Datums-Entität antippen und das heutige Datum setzen — *Nächste …* und die Fällig-Anzeige aktualisieren sich sofort.

Bei jeder echten Benutzeränderung feuert die Integration das Event **`flappie_health_updated`** mit `cat_id`, `cat_name`, `health_type` (`worms`/`fleas`/`vet`), `last`, `interval_months` und `next_due` (ISO-Datum). Für Kalendereinträge dieses Event verwenden — *nicht* einen State-Trigger auf die Sensoren, denn Zustandswechsel passieren auch bei HA-Neustarts und würden Duplikate erzeugen:

```yaml
automation:
  - alias: "Katzengesundheit: Kalendereintrag"
    triggers:
      - trigger: event
        event_type: flappie_health_updated
    actions:
      - action: calendar.create_event
        target:
          entity_id: calendar.familie
        data:
          summary: >-
            🐱 {{ trigger.event.data.cat_name }} {{ {'worms': 'Wurmkur',
            'fleas': 'Flohbehandlung', 'vet': 'Arztbesuch'}[trigger.event.data.health_type] }}
          start_date: "{{ trigger.event.data.next_due }}"
          end_date: "{{ (trigger.event.data.next_due | as_datetime + timedelta(days=1)).date() }}"
    mode: queued
```

Erinnerungs-Automatisierung:

```yaml
automation:
  - alias: "Katzengesundheit: Wurmkur-Erinnerung"
    triggers:
      - trigger: state
        entity_id: binary_sensor.<katze>_wurmkur_fallig
        to: "on"
    actions:
      - action: notify.mobile_app_dein_handy
        data:
          title: "💊 Wurmkur fällig"
          message: "Zeit für die nächste Wurmkur."
```

## Langzeitstatistiken

Die Integration importiert zwei externe Statistiken, nutzbar in der *Statistik-Diagramm*-Karte (sie erscheinen auch in den Statistik-Auswahlfeldern):

| Statistik-ID | Inhalt | Backfill |
|---|---|---|
| `flappie:activity_daily` | Ereignisse pro Tag | Letzte 7 Tage bei Installation (Cloud-Aufbewahrung), wächst danach täglich |
| `flappie:prey_daily` | Beutefunde pro Tag | **Volle Historie seit Registrierung der Klappe** |

Beispielkarte:

```yaml
type: statistics-graph
title: Aktivität pro Tag
chart_type: bar
period: day
days_to_show: 14
stat_types:
  - change
entities:
  - flappie:activity_daily
```

## Dashboard-Beispiel

Ein komplettes dreispaltiges Sections-Dashboard (Steuerung / letzte Ereignisse mit Direktbutton zur Video-Medienquelle / Katzen & Statistiken) liegt in [`docs/dashboard.yaml`](docs/dashboard.yaml). Entity-IDs an die eigenen anpassen (sie hängen von Geräte-/Bereichsnamen ab).

Tipp — Direktlink zur Flappie-Videoliste aus jeder Button-Karte:

```yaml
tap_action:
  action: navigate
  navigation_path: /media-browser/browser/app%2Cmedia-source%3A%2F%2Fflappie
```

## Automatisierungs-Beispiel

Benachrichtigung, wenn die Katze Beute mitbringt und die Klappe sperrt:

```yaml
automation:
  - alias: "Flappie: Beute-Alarm"
    triggers:
      - trigger: state
        entity_id: event.<name>_klappen_ereignis
    conditions:
      - condition: template
        value_template: "{{ trigger.to_state.attributes.event_type == 'prey' }}"
    actions:
      - action: notify.mobile_app_dein_handy
        data:
          title: "🐭 Beute erkannt!"
          message: "Die Klappe wurde gesperrt."
```

## API-Hinweise & Einschränkungen

Hart erarbeitetes Wissen über die Flappie-Cloud, damit es niemand neu entdecken muss:

- **Nur Cloud-Polling.** Intervall 60 s (die inoffizielle API-Etikette bittet um ≥ 30 s). Ereignisse kommen daher mit bis zu einer Minute Verzögerung — die Cloud bietet keinen Push für Drittanbieter.
- **Ereignisse („Bundles") verfallen serverseitig nach 7 Tagen.** Deshalb bezieht der Sensor *Letztes Beute-Ereignis* sein Datum aus `latest_prey_detection` des Cloud-Dashboards statt aus der Ereignisliste — dieses Feld ist dauerhaft.
- **Medien-URLs sind kurzlebige signierte Links.** Die Integration fordert direkt vor dem Ausliefern eines Bilds bzw. Abspielen eines Videos immer eine frische URL an.
- **Die Listenfilter `fromCreatedAt`/`toCreatedAt` werden vom Backend ignoriert** (verifiziert 08/2026). Tageszähler werden clientseitig durch Paginieren der Ereignisliste berechnet.
- **Die Beute-Statistikserie kommt absteigend sortiert** — bei eigener Weiterverarbeitung auf die Reihenfolge achten.
- **Keine Richtungsinformation.** Die Kamera schaut nach draußen; die API unterscheidet nicht zwischen Rein und Raus. „Aktivität" zählt Klappen-Ereignisse.
- **RFID:** Das Settings-Flag existiert im Backend, aber laut Hersteller liest die Klappe keine Mikrochips; selektiver Zutritt ist das kamerabasierte „Cat ID". Der Schalter ist standardmäßig deaktiviert, seine Wirkung unbekannt.
- **Zeitstempel der Cloud sind zeitzonen-naiv in der Geräte-Zeitzone** (`zone_info`), *nicht* UTC — verifiziert anhand eines realen Durchgangs. Die Integration interpretiert sie in der HA-Zeitzone, die in der Praxis der `zone_info` der Klappe entspricht.
- **Verarbeitungslatenz der Cloud:** Ein Klappen-Ereignis wird erst ~5–10 Minuten nach dem Durchgang in der Cloud sichtbar (App *und* API) — die Klappe lädt das Video hoch und die KI analysiert es. Dazu kommen bis zu 60 s Polling in Home Assistant.

## Fehlerbehebung

- **„Ungültige Anmeldedaten" bei der Einrichtung** — es gelten die Zugangsdaten des Flappie-*App*-Kontos (E-Mail + Passwort). Für Konten mit Apple-/Google-Login ggf. zuerst in der App ein Passwort setzen.
- **Reauth-Schleife** — das Passwort wurde geändert; den Reauth-Flow aus der Benachrichtigung abschließen.
- **Statistiken fehlen** — der Import läuft stündlich (und einmal direkt nach dem Start); unter *Einstellungen → System → Protokolle* nach `flappie`-Warnungen suchen.
- Debug-Logging:

  ```yaml
  logger:
    logs:
      custom_components.flappie: debug
  ```

## Credits

- API-Reverse-Engineering: [`flappie-api`](https://github.com/ooswald/flappie-api) (npm) von Olivier Oswald, MIT
- Diese Integration wurde mit [Claude Code](https://claude.com/claude-code) gebaut.

## Lizenz

[MIT](LICENSE) — nicht mit Flappie Technologies AG assoziiert. Nutzung auf eigene Gefahr.
