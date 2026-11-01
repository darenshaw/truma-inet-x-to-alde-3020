# Dashboard card

[← README](../README.md)

The integration ships a thermostat card whose dial follows the mode: it sets the
temperature while heating, the fan speed while venting, and is disabled while
off. Home Assistant's own climate dial is bound to temperature and humidity
only, and climate fan modes are arbitrary strings rather than a numeric range,
so core cannot put fan speed on an arc.

**Nothing to install.** The integration serves the card at
`/truma_inetx/truma-climate-dial-card.js` and registers it with the frontend, so
it arrives and updates with the integration. Add it the ordinary way: edit a
dashboard, **+ Add card**, search for *Truma*. The picker shows a live dial and
the editor opens with this integration's climate entity already filled in — the
card carries a `getStubConfig` and a `getConfigForm`. Only the name is left, and
it is optional.

The **By entity** tab will not offer it: Home Assistant builds those suggestions
from core card types alone, and a custom card has no way in.

In YAML, if you would rather:

```yaml
type: custom:truma-climate-dial-card
entity: climate.truma_inetx_ffb4d1
name: Heating          # optional
```

## Why it ships this way

A HACS repository belongs to exactly one category, so this repository cannot
also be published as a HACS *plugin*. Serving the card from the integration
avoids a second repository to version and tag. The integration version is
appended to the URL as a query string, because the frontend service worker
caches assets for weeks and a browser hard-refresh does not bypass it — without
a changing URL an updated card would never reach the browser.

The trade-off: `add_extra_js_url` loads the module on every page load for every
user, not only when the card is on screen. About 19 KB.

The card does not reimplement the dial. It instantiates Home Assistant's own
`ha-control-circular-slider` and `ha-outlined-icon-button` and reuses the
frontend's layout CSS, so it inherits upstream's appearance and behaviour. Those
are internal frontend components with no stability guarantee: upstream
restyling arrives for free, an upstream rename breaks the card, which then
renders an explicit error naming the missing component.

## Custom card: dial plus buttons

*Added in `0.9.0b25+alde3020.6`.*

A second card ships alongside the first: `truma-climate-dial-custom-card`,
shown in the card picker as **Truma climate dial (custom)**. It is the same dial,
because it subclasses `truma-climate-dial-card` and waits for that element to
be defined first. Beneath the dial it can add a row of controls for the
heater's switches and selects, so one card covers everything you use day to day.

What it adds:

- **Power button** (top right, round). It switches between `off` and the first
  non-off HVAC mode (`heat` when offered), or `power_on_mode` if set. It lights
  while heating is on and dims while it waits for the panel to confirm over BLE.
- **HVAC mode row**, hidden by default (`show_hvac_modes: true`). It shows only
  the modes the entity reports, so an Alde has no fan button, and stretches the
  buttons to the full card width.
- **Two button rows** (`row_1`, `row_2`), up to three buttons each, sharing
  the row width equally.
  - Tap: switches / input_booleans / lights / fans toggle; selects open an
    inline option list; buttons are pressed; anything else opens more-info.
  - Long-press or right-click: more-info.
  - Names drop the device prefix ("Alde Compact 3020 HE Electric heating" →
    "Electric heating"). A select lights only when it has an `off` option and is
    not on it.
- **Styling** in the visual editor (colours, opacity, borders, text and icon
  sizes, how "on" is shown: `background` | `border` | `both`). Every key can
  also be overridden per button.

```yaml
type: custom:truma-climate-dial-custom-card
entity: climate.alde_compact_3020_he
name: Heating                 # optional
show_power_button: true       # optional, default true
power_on_mode: heat           # optional
show_hvac_modes: false        # optional, default false
state_indicator: border       # background (default) | border | both
row_1:                        # max 3; entity ids or objects
  - switch.alde_compact_3020_he_water_boost
  - entity: switch.alde_compact_3020_he_hot_water
    name: Hot Water
    icon: mdi:water-boiler
row_2:
  - select.alde_compact_3020_he_electric_heating
```

The full list of keys is in the header comment of
`frontend/truma-climate-dial-custom-card.js`.

It is served and registered the same way as the base card
(`/truma_inetx/truma-climate-dial-custom-card.js`, through `add_extra_js_url`).
Its URL carries the integration version and the file's modification time, so an
edit to the card reaches the browser past the service-worker cache without a
version bump. It adds about 28 KB to every page load.
