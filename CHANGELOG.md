# Changelog

Changes to the Alde Compact 3020 build of the Truma iNet X integration.
Versions follow `manifest.json` (`<upstream>+alde3020.<n>`).

## 0.9.0b25+alde3020.8 — 2026-11-27

### Added
- **Timers run by Home Assistant.** Six timers, all on one **iNet X Timers**
  device under the panel (one device, so the device list stays short), named
  "Timer 1 enabled", "Timer 1 start" and so on. Each timer has:
  - **Enabled**;
  - **Controls**: Heating, Hot water, or Heating and hot water;
  - **Start** and **End** times (an end before the start runs past midnight);
  - **Temperature** for heating (5–30 °C);
  - **Days**: Every day, Weekdays or Weekends (the days the timer starts on).

  At a start, heating is set to the timer's temperature and/or the hot water is
  switched on. At an end, control passes to any other timer still running, or
  the heating is turned off / the hot water switched off. If timers overlap,
  the one that started most recently wins. Heating and hot water are worked
  out separately. The timers act only when the running timer changes, so a
  manual change in the middle of a timer stands until the next change. A
  command that fails, for example with the panel out of range, is retried
  every minute. Settings survive restarts.

  These are separate from the panel's own timers, which describe their
  settings as read-only and hold no temperature. Keep the panel's timer
  switches off so the two don't conflict.

## 0.9.0b25+alde3020.7 — 2026-11-26

### Added
- **"Only create entities for detected hardware"** option (Settings → Devices
  & services → Truma iNet X → Configure). It is on by default, which keeps the
  existing behaviour. When off, every entity the integration can map is
  created:
  - parameters no device on your bus publishes go on a **Not detected**
    device. They are always unavailable, so you can hide or disable the
    ones you don't want;
  - timer slots the panel marks as empty are created too;
  - if that hardware turns up later, its real entity is created on its own
    device and the placeholder is removed.
  Changing the option reloads the integration. Turning it back on removes the
  Not detected device, its entities and the empty timer slots.

### Fixed
- **Entities no longer vanish when the panel is out of range at startup.**
  Entities are built from what the panel has published, and the bus started
  empty on every Home Assistant start, so a restart with the vehicle switched
  off or out of Bluetooth range created no entities at all and dashboards
  showed "entity not found". The coordinator now saves the last known bus
  (devices, parameters and descriptions) in its existing storage file, once
  discovery finishes and at most once a minute after that. It restores the
  bus at startup, so every entity is created straight away and stays
  *unavailable* until a live session replaces the stored values.

## 0.9.0b25+alde3020.6 — 2026-11-01

### Added
- **Custom dashboard card** `custom:truma-climate-dial-custom-card`
  (*Truma climate dial (custom)* in the card picker). It extends the bundled
  thermostat dial with:
  - a round power button (off ↔ heat) that lights while heating is on;
  - an optional HVAC mode row showing only the modes the entity reports;
  - up to two rows of up to three buttons for switches, selects and buttons,
    sharing the row width equally (tap to toggle, pick or press; long-press
    for more-info);
  - colour, border, opacity and text-size options in the visual editor,
    overridable per button.
  See [docs/card.md](docs/card.md#custom-card-dial-plus-buttons).

### Changed
- `__init__.py` now serves and registers
  `frontend/truma-climate-dial-custom-card.js` alongside the base card. The
  card's URL is cache-busted with the integration version plus the file's
  modification time.
- README and `docs/card.md` document the new card. The README summary at the top
  now lists both dashboard cards.
- Links now point to this repository instead of upstream: `codeowners`
  (`@darenshaw`), the "Learn more" link on the can't-reach-panel repair issue,
  the base card's documentation link, and the README CI badge. README now asks
  for all issues with this build to be reported here. The credit to upstream
  (rpodgorny/hass-truma-inetx) stays, as GPL-3.0 requires.

## 0.9.0b25+alde3020.5 and earlier

See the git history. The Alde Compact 3020 changes up to this point are
documented in [docs/alde-3020.md](docs/alde-3020.md).
