# Effe ECC (My Effe) for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)

Unofficial Home Assistant integration for **Effe** steam baths (hammam) and saunas with the
**current-generation ECC module** — the one that is set up over Bluetooth and controlled with the
"My Effe" app. It uses the same cloud API as the app; state changes arrive by push.

> The module has no usable local API: its only open port (81) is an authenticated WebSocket that
> the app itself never uses. The integration therefore needs internet access and the Effe cloud.
> Older modules (TCP port 8899, "Effe ECC" app) are not supported.

Not affiliated with or endorsed by Effegibi S.r.l.

## Installation (HACS)

1. HACS → ⋮ → **Custom repositories**
2. Add `https://github.com/Spionkiller01/ha-effe-sauna`, type **Integration**
3. Install "Effe ECC (My Effe)" and restart Home Assistant
4. **Settings → Devices & services → Add integration → Effe ECC (My Effe)** and sign in with
   your My Effe e-mail and password

Manual: copy `custom_components/effe_sauna/` to `config/custom_components/`.

## Features

Tested on a steam bath (system type `inside`, firmware `EHST10TE`).

| Entity | Function |
|---|---|
| `climate` | Steam on/off, steam level low/medium/high (42/44/46 °C) as preset |
| `light` Light | Cabin light on/off |
| `light` Chromotherapy | On/off, 9 programmes as effects (red, yellow, green, blue, light blue, sunrise, sunset, sea, forest) |
| `switch` Control panel | Panel on/off |
| `switch` Mood light | Only if present and enabled on the device |
| `sensor` | Steam setpoint; diagnostic: timer setting, active alarms, last seen, IP address |
| `binary_sensor` | Door, ready, steam, paused, warm bench, alarm; diagnostic: service due, cloud push |

For saunas the integration creates heater on/off, light, chromotherapy, mood light, infrared and
biosauna plus read-only temperature and humidity setpoints. **The sauna part is untested** —
reports are welcome.

### Limitations

- **No measured temperature:** the cloud only reports setpoints.
- **No free setpoint:** the app only knows the three steam levels; the integration sends nothing else.
- **No dimming, warm-bench control or schedules:** no verified commands are known for these.

## Safety

- Only commands the official app sends are used.
- Steam, sauna, infrared and biosauna are not started while the module reports an open door or
  an alarm. The interlocks of the controller and the cloud apply on top of that.
- Remotely starting a heater is your responsibility — make sure the cabin is safe to heat.

## Reporting problems

**Settings → Devices & services → Effe ECC → ⋮ → Download diagnostics** contains the current
state and the last 50 raw messages (credentials and identifiers are redacted). Please attach it
to your issue.
