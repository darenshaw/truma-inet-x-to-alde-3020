# Changelog

Changes to the Alde Compact 3020 build of the Truma iNet X integration.
Versions follow `manifest.json` (`<upstream>+alde3020.<n>`).

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
