# Effe ECC (My Effe) für Home Assistant

Inoffizielle Integration für Effe-Dampfbäder und -Saunen mit **ECC-Modul der neuesten Generation**
(Einrichtung per Bluetooth, Bedienung über die App „My Effe"). Die Integration nutzt dieselbe
Cloud-Schnittstelle wie die App; Statusänderungen kommen per Push.

> Das Modul hat keine nutzbare lokale Schnittstelle: Der einzige offene Port (81) ist ein
> WebSocket mit Anmeldung, den auch die App nicht benutzt. Ohne Internet und Effe-Cloud
> funktioniert die Integration daher nicht. Ältere Module (Port 8899, App „Effe ECC") werden
> nicht unterstützt.

## Installation über HACS

1. HACS → ⋮ → **Benutzerdefinierte Repositories**
2. `https://github.com/Spionkiller01/ha-effe-sauna` eintragen, Typ **Integration**
3. „Effe ECC (My Effe)" installieren und Home Assistant neu starten
4. **Einstellungen → Geräte & Dienste → Integration hinzufügen → Effe ECC (My Effe)**,
   E-Mail und Passwort des My-Effe-Kontos eingeben

Manuell: Ordner `custom_components/effe_sauna/` nach `config/custom_components/` kopieren.

## Unterstützte Funktionen

Getestet an einem Dampfbad (Systemtyp `inside`, Firmware `EHST10TE`).

| Entität | Funktion |
|---|---|
| `climate` | Dampf ein/aus, Dampfstufe niedrig/mittel/hoch (42/44/46 °C) als Voreinstellung |
| `light` Licht | Kabinenlicht ein/aus |
| `light` Farblicht | ein/aus, 9 Programme als Effekt (Rot, Gelb, Grün, Blau, Hellblau, Sonnenaufgang, Sonnenuntergang, Meer, Wald) |
| `switch` Bedienfeld | Bedienfeld ein/aus |
| `switch` Mood-Licht | nur wenn am Gerät vorhanden und freigeschaltet |
| `sensor` | Dampf-Solltemperatur; Diagnose: Timer-Einstellung, aktive Alarme, zuletzt gesehen, IP-Adresse |
| `binary_sensor` | Tür, bereit, Dampf, pausiert, Wärmebank, Alarm; Diagnose: Wartung fällig, Cloud-Push |

Für Saunen sind Heizung ein/aus, Licht, Farblicht, Mood-Licht, Infrarot und Biosauna sowie
Solltemperatur und Soll-Luftfeuchte (nur lesend) angelegt, aber **ungetestet**.

### Was nicht geht

- **Ist-Temperatur:** Die Cloud liefert keinen Messwert, nur Sollwerte.
- **Freie Solltemperatur:** Die App kennt nur die drei Dampfstufen; andere Werte sendet die Integration nicht.
- **Dimmen, Wärmebank schalten, Zeitprogramme:** dafür sind keine geprüften Befehle bekannt.

## Sicherheit

- Es werden nur Befehle gesendet, die auch die App sendet.
- Dampf, Sauna, Infrarot und Biosauna startet die Integration nicht, solange das Modul die Tür
  als offen oder einen Alarm meldet. Die Sperren von Steuerung und Cloud gelten zusätzlich.
- Die Dampfstufe wird ohne eigenes „Dampf ein" gesendet; ob die Steuerung dabei selbst startet,
  ist nicht geprüft. Die Sicherheitsprüfung gilt deshalb auch dafür.

## Fehler melden

**Einstellungen → Geräte & Dienste → Effe ECC → ⋮ → Diagnose herunterladen** enthält den
aktuellen Zustand und die letzten 50 Rohnachrichten (Zugangsdaten und Kennungen sind geschwärzt).
