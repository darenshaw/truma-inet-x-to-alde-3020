/*
 * truma-climate-dial-custom-card
 *
 * The integration's truma-climate-dial-card (same dial, same behaviour) plus:
 *   - HVAC mode buttons limited to the modes the entity actually reports
 *     (an Alde has no fan mode), stretched to the full card width;
 *   - up to two rows of up to three extra buttons for switches / selects.
 *     Buttons share the row width equally: 2 buttons -> halves, 3 -> thirds.
 *
 * Tap:  switch / input_boolean / light / fan  -> toggle
 *       select / input_select                 -> option list drops down
 *       button / input_button                 -> press
 *       anything else                         -> more-info
 * Long-press (or right-click) any button      -> more-info
 *
 * Usage:
 *   type: custom:truma-climate-dial-custom-card
 *   entity: climate.alde_compact_3020_he
 *   name: Heating                 # optional
 *   show_power_button: true       # optional, default true: round power
 *                                 # button top right, lit while heating is on
 *   power_on_mode: heat           # optional, mode the power button turns on
 *   power_color: orange           # optional, power button colour when on
 *   show_hvac_modes: false        # optional, default false: the old mode row
 *   row_1:                        # max 3; plain entity ids or objects
 *     - switch.alde_compact_3020_he_water_boost
 *     - entity: switch.alde_compact_3020_he_hot_water
 *       name: Hot Water
 *       icon: mdi:water-boiler
 *   row_2:
 *     - select.alde_compact_3020_he_electric_heating
 *
 * Button appearance (card-wide; every key can also be set on a single button
 * in its object form to override the card-wide value):
 *   show_icons: false             # per button: show_icon: false
 *   active_color: orange          # background when on (theme name or CSS colour)
 *   active_text_color: white      # text/icon colour when on
 *   inactive_color: "#333"        # background when off
 *   active_opacity: 60            # % opacity of the on background (0-100)
 *   inactive_opacity: 30          # % opacity of the off background (0-100)
 *   border_width: 2               # px, 0 = no border
 *   border_color: amber           # border colour (off and on)
 *   active_border_color: orange   # border colour when on (defaults to border_color)
 *   state_indicator: border       # how "on" is shown: background (default) | border | both
 *   active_border_width: 3        # px, border width when on (border/both; default 2 or border_width)
 *   state_color: grey             # colour of the state line (On / Off / 2 kW)
 *   icon_size: 24                 # px
 *   name_size: 13                 # px
 *   name_weight: 500              # 300 light .. 700 bold
 *   state_size: 12                # px
 *   state_weight: 400
 *
 * It subclasses truma-climate-dial-card, so it waits for that element (served
 * by the same integration) before defining itself. That also inherits the
 * base card's fix for the scoped-custom-element-registry race.
 */

const BASE_TAG = "truma-climate-dial-card";
const TAG = "truma-climate-dial-custom-card";
const MAX_PER_ROW = 3;
// mdi:power
const POWER_ICON = "M16.56,5.44L15.11,6.89C16.84,7.94 18,9.83 18,12A6,6 0 0,1 12,18A6,6 0 0,1 6,12C6,9.83 7.16,7.94 8.88,6.88L7.44,5.44C5.36,6.88 4,9.28 4,12A8,8 0 0,0 12,20A8,8 0 0,0 20,12C20,9.28 18.64,6.88 16.56,5.44M13,3H11V13H13V3Z";
const LONG_PRESS_MS = 500;

const TOGGLE_DOMAINS = ["switch", "input_boolean", "light", "fan", "automation"];
const SELECT_DOMAINS = ["select", "input_select"];
const PRESS_DOMAINS = ["button", "input_button"];

const DEFAULT_ICONS = {
  switch: "mdi:toggle-switch-variant",
  input_boolean: "mdi:toggle-switch-variant",
  select: "mdi:format-list-bulleted",
  input_select: "mdi:format-list-bulleted",
  button: "mdi:gesture-tap-button",
  input_button: "mdi:gesture-tap-button",
  light: "mdi:lightbulb",
  fan: "mdi:fan",
};

const WEIGHTS = [
  { value: "300", label: "Light" },
  { value: "400", label: "Normal" },
  { value: "500", label: "Medium" },
  { value: "700", label: "Bold" },
];

const LABELS = {
  show_icons: "Show icons",
  power_color: "Power button colour when on",
  state_indicator: "Show 'on' using",
  active_border_width: "Border width when on",
  active_color: "Colour when on",
  active_text_color: "Text colour when on",
  inactive_color: "Colour when off",
  state_color: "Status text colour (On/Off line)",
  active_opacity: "Opacity when on (%)",
  inactive_opacity: "Opacity when off (%)",
  border_width: "Border width",
  border_color: "Border colour",
  active_border_color: "Border colour when on",
  icon_size: "Icon size",
  name_size: "Button name size",
  name_weight: "Button name weight",
  state_size: "Status text size",
  state_weight: "Status text weight",
  entity: "Climate entity",
  name: "Name",
  show_hvac_modes: "Show HVAC mode row",
  show_power_button: "Show power button (top right)",
  row_1: "Row 1 buttons (max 3)",
  row_2: "Row 2 buttons (max 3)",
};

// config key -> [css variable, kind]
const STYLE_KEYS = {
  active_color: ["--tx-active-bg", "color"],
  active_text_color: ["--tx-active-fg", "color"],
  inactive_color: ["--tx-bg", "color"],
  inactive_text_color: ["--tx-fg", "color"],
  active_opacity: ["--tx-active-alpha", "pct"],
  inactive_opacity: ["--tx-alpha", "pct"],
  border_width: ["--tx-border-w", "px"],
  border_color: ["--tx-border-c", "color"],
  active_border_color: ["--tx-active-border-c", "color"],
  active_border_width: ["--tx-active-border-w", "px"],
  state_color: ["--tx-state-color", "color"],
  power_color: ["--tx-power-color", "color"],
  icon_size: ["--tx-icon-size", "px"],
  name_size: ["--tx-name-size", "px"],
  name_weight: ["--tx-name-weight", "raw"],
  state_size: ["--tx-state-size", "px"],
  state_weight: ["--tx-state-weight", "raw"],
};

// Accepts a theme colour name from the ui_color picker ("red", "primary"),
// an [r, g, b] list, or any CSS colour ("#ff8800", "rgb(...)", "var(--x)").
function cssColor(v) {
  if (Array.isArray(v)) return `rgb(${v.join(",")})`;
  const t = String(v).trim();
  // ui_color picker specials. "none" must become a real colour: an invalid
  // value inside var() makes the browser drop the whole border declaration.
  if (t === "" || t === "default" || t === "state") return null;
  if (t === "none") return "transparent";
  if (/^(#|rgb|hsl|var\()/i.test(t)) return t;
  if (t === "primary" || t === "accent") return `var(--${t}-color)`;
  return `var(--${t}-color, ${t})`;
}

function applyStyleVars(el, cfg) {
  if (!cfg) return;
  for (const [key, [cssVar, kind]] of Object.entries(STYLE_KEYS)) {
    const v = cfg[key];
    if (v === undefined || v === null || v === "") continue;
    const val = kind === "color" ? cssColor(v)
      : kind === "pct" ? `${Math.min(Math.max(Number(v), 0), 100)}%`
      : kind === "px" && /^\d+(\.\d+)?$/.test(String(v)) ? `${v}px` : String(v);
    if (val === null) continue;
    el.style.setProperty(cssVar, val);
  }
}

function normaliseRow(row, which) {
  if (row === undefined || row === null || row === "") return [];
  if (!Array.isArray(row)) throw new Error(`${which} must be a list`);
  const items = row
    .filter((x) => x)
    .map((x) => (typeof x === "string" ? { entity: x } : { ...x }));
  for (const it of items) {
    if (!it.entity) throw new Error(`Every ${which} button needs an entity`);
  }
  if (items.length > MAX_PER_ROW) {
    throw new Error(`${which} can have at most ${MAX_PER_ROW} buttons`);
  }
  return items;
}

function define() {
  const Base = customElements.get(BASE_TAG);

  class TrumaClimateDialCustomCard extends Base {
    static getConfigForm() {
      const extraDomains = [...TOGGLE_DOMAINS, ...SELECT_DOMAINS, ...PRESS_DOMAINS, "number", "sensor", "binary_sensor"];
      return {
        schema: [
          { name: "entity", required: true, selector: { entity: { domain: "climate" } } },
          { name: "name", selector: { text: {} } },
          { name: "show_power_button", selector: { boolean: {} } },
          { name: "row_1", selector: { entity: { multiple: true, domain: extraDomains } } },
          { name: "row_2", selector: { entity: { multiple: true, domain: extraDomains } } },
          {
            name: "",
            type: "expandable",
            flatten: true,
            title: "Buttons: colours",
            icon: "mdi:palette",
            schema: [
              {
                name: "",
                type: "grid",
                flatten: true,
                schema: [
                  { name: "state_indicator", selector: { select: { mode: "dropdown", options: [ { value: "background", label: "Background colour" }, { value: "border", label: "Border colour" }, { value: "both", label: "Background and border" } ] } } },
                  { name: "show_icons", selector: { boolean: {} } },
                  { name: "active_color", selector: { ui_color: { include_none: true } } },
                  { name: "active_text_color", selector: { ui_color: { include_none: true } } },
                  { name: "inactive_color", selector: { ui_color: { include_none: true } } },
                  { name: "state_color", selector: { ui_color: { include_none: true } } },
                  { name: "power_color", selector: { ui_color: { include_none: true } } },
                  { name: "active_opacity", selector: { number: { min: 0, max: 100, step: 5, mode: "slider", unit_of_measurement: "%" } } },
                  { name: "inactive_opacity", selector: { number: { min: 0, max: 100, step: 5, mode: "slider", unit_of_measurement: "%" } } },
                ],
              },
            ],
          },
          {
            name: "",
            type: "expandable",
            flatten: true,
            title: "Buttons: borders",
            icon: "mdi:border-all-variant",
            schema: [
              {
                name: "",
                type: "grid",
                flatten: true,
                schema: [
                  { name: "border_width", selector: { number: { min: 0, max: 8, step: 1, mode: "box", unit_of_measurement: "px" } } },
                  { name: "border_color", selector: { ui_color: { include_none: true } } },
                  { name: "active_border_width", selector: { number: { min: 0, max: 8, step: 1, mode: "box", unit_of_measurement: "px" } } },
                  { name: "active_border_color", selector: { ui_color: { include_none: true } } },
                ],
              },
            ],
          },
          {
            name: "",
            type: "expandable",
            flatten: true,
            title: "Buttons: text and icons",
            icon: "mdi:format-size",
            schema: [
              {
                name: "",
                type: "grid",
                flatten: true,
                schema: [
                  { name: "name_size", selector: { number: { min: 8, max: 32, step: 1, mode: "box", unit_of_measurement: "px" } } },
                  { name: "name_weight", selector: { select: { mode: "dropdown", options: WEIGHTS } } },
                  { name: "state_size", selector: { number: { min: 8, max: 32, step: 1, mode: "box", unit_of_measurement: "px" } } },
                  { name: "state_weight", selector: { select: { mode: "dropdown", options: WEIGHTS } } },
                  { name: "icon_size", selector: { number: { min: 12, max: 48, step: 1, mode: "box", unit_of_measurement: "px" } } },
                ],
              },
            ],
          },
        ],
        computeLabel: (s) => LABELS[s.name],
      };
    }

    setConfig(config) {
      const rows = [normaliseRow(config && config.row_1, "Row 1"), normaliseRow(config && config.row_2, "Row 2")];
      super.setConfig(config);
      this._rows = rows;
      this._openSelect = null; // "r-i" key of the select whose list is open
    }

    getCardSize() {
      return 5 + this._rows.filter((r) => r.length).length;
    }

    getGridOptions() {
      return { columns: 12, min_columns: 6 };
    }

    /* ---------- dom ---------- */

    _build() {
      super._build();
      const card = this.shadowRoot.querySelector("ha-card");

      const style = document.createElement("style");
      style.textContent = `
        ha-card { position: relative; }
        .name { padding-right: 56px; min-height: 40px; display: flex; align-items: center; }
        .power {
          position: absolute; top: 12px; right: 12px; z-index: 1;
          width: 44px; height: 44px; border-radius: 50%; padding: 0;
          display: flex; align-items: center; justify-content: center; cursor: pointer;
          box-sizing: border-box; -webkit-tap-highlight-color: transparent;
          border: var(--tx-border-w, 0px) solid var(--tx-border-c, var(--divider-color, #e0e0e0));
          background: color-mix(in srgb, var(--tx-bg, var(--divider-color, #e0e0e0)) var(--tx-alpha, 100%), transparent);
          color: var(--tx-fg, var(--primary-text-color));
          transition: background 0.2s, color 0.2s, box-shadow 0.2s;
        }
        .power svg { width: 26px; height: 26px; }
        .power.on {
          background: var(--tx-power-color, var(--tx-active-bg, var(--state-climate-heat-color, #ff8100)));
          color: var(--tx-active-fg, #fff);
          box-shadow: 0 0 10px 2px color-mix(in srgb, var(--tx-power-color, var(--tx-active-bg, var(--state-climate-heat-color, #ff8100))) 60%, transparent);
        }
        .power.ind-border.on {
          background: color-mix(in srgb, var(--tx-bg, var(--divider-color, #e0e0e0)) var(--tx-alpha, 100%), transparent);
          color: var(--tx-power-color, var(--tx-active-bg, var(--state-climate-heat-color, #ff8100)));
          border: max(var(--tx-border-w, 0px), 2px) solid var(--tx-power-color, var(--tx-active-border-c, var(--tx-active-bg, var(--state-climate-heat-color, #ff8100))));
        }
        .power.busy { opacity: 0.6; }
        .power[hidden] { display: none; }
        .modes { gap: 8px; }
        .modes button { flex: 1 1 0; width: auto; border-radius: 12px; height: 48px;
          background: color-mix(in srgb, var(--tx-bg, var(--divider-color, #e0e0e0)) var(--tx-alpha, 100%), transparent); color: var(--tx-fg, var(--primary-text-color));
          box-sizing: border-box; border: var(--tx-border-w, 0px) solid var(--tx-border-c, var(--divider-color, #e0e0e0)); }
        .modes button[aria-pressed="true"] {
          background: color-mix(in srgb, var(--tx-active-bg, var(--primary-color)) var(--tx-active-alpha, 100%), transparent); color: var(--tx-active-fg, var(--text-primary-color, #fff)); border-color: var(--tx-active-border-c, var(--tx-border-c, var(--divider-color, #e0e0e0))); border-width: var(--tx-active-border-w, var(--tx-border-w, 0px)); }
        .modes button[hidden] { display: none; }
        .rows { display: flex; flex-direction: column; gap: 8px; margin-top: 8px; }
        .row { display: flex; gap: 8px; }
        .row[hidden] { display: none; }
        .xbtn {
          flex: 1 1 0; min-width: 0;
          display: flex; flex-direction: column; align-items: center; justify-content: center;
          gap: 2px; padding: 8px 4px; min-height: 64px;
          box-sizing: border-box; border: var(--tx-border-w, 0px) solid var(--tx-border-c, var(--divider-color, #e0e0e0)); border-radius: 12px; cursor: pointer;
          background: color-mix(in srgb, var(--tx-bg, var(--divider-color, #e0e0e0)) var(--tx-alpha, 100%), transparent); color: var(--tx-fg, var(--primary-text-color));
          font: inherit; -webkit-tap-highlight-color: transparent; user-select: none;
        }
        .xbtn.active { background: color-mix(in srgb, var(--tx-active-bg, var(--primary-color)) var(--tx-active-alpha, 100%), transparent); color: var(--tx-active-fg, var(--text-primary-color, #fff)); border-color: var(--tx-active-border-c, var(--tx-border-c, var(--divider-color, #e0e0e0))); border-width: var(--tx-active-border-w, var(--tx-border-w, 0px)); }
        .xbtn.noicon .ic { display: none; }
        /* state_indicator: border / both. On is shown by the border, which
           defaults to the "on" colour and is at least 2px so it is visible. */
        .xbtn.ind-border.active, .modes.ind-border button[aria-pressed="true"] {
          background: color-mix(in srgb, var(--tx-bg, var(--divider-color, #e0e0e0)) var(--tx-alpha, 100%), transparent); color: var(--tx-fg, var(--primary-text-color)); }
        .xbtn.ind-border.active, .modes.ind-border button[aria-pressed="true"],
        .xbtn.ind-both.active, .modes.ind-both button[aria-pressed="true"] {
          border-style: solid;
          border-width: var(--tx-active-border-w, max(var(--tx-border-w, 0px), 2px));
          border-color: var(--tx-active-border-c, var(--tx-active-bg, var(--primary-color))); }
        .xbtn.ind-border.active .s { color: var(--tx-state-color, inherit); }
        .xbtn.open { outline: 2px solid var(--primary-color); outline-offset: 1px; }
        .xbtn.unavailable { opacity: 0.45; }
        .xbtn ha-icon, .xbtn ha-state-icon { --mdc-icon-size: var(--tx-icon-size, 24px); }
        .xbtn .n, .xbtn .s {
          max-width: 100%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
        }
        .xbtn .n { font-size: var(--tx-name-size, 13px); font-weight: var(--tx-name-weight, 500); }
        .xbtn .s { font-size: var(--tx-state-size, 12px); font-weight: var(--tx-state-weight, 400);
                   opacity: 0.8; color: var(--tx-state-color, inherit); }
        .xbtn.active .s { color: var(--tx-state-color, inherit); }
        .opts { display: flex; flex-wrap: wrap; gap: 6px; padding: 8px;
                border-radius: 12px; background: var(--secondary-background-color, #f5f5f5); }
        .opts[hidden] { display: none; }
        .opts button {
          flex: 1 1 0; min-width: 64px; height: 40px; border: none; border-radius: 10px; cursor: pointer;
          background: var(--card-background-color, #fff); color: var(--primary-text-color); font: inherit;
        }
        .opts button.sel { background: var(--primary-color); color: var(--text-primary-color, #fff); }
      `;
      this.shadowRoot.append(style);

      applyStyleVars(card, this._config);

      const rowsEl = document.createElement("div");
      rowsEl.className = "rows";
      card.querySelector(".body").append(rowsEl);

      this._rowEls = this._rows.map((items, r) => {
        const rowEl = document.createElement("div");
        rowEl.className = "row";
        rowEl.hidden = items.length === 0;
        const opts = document.createElement("div");
        opts.className = "opts";
        opts.hidden = true;
        rowsEl.append(rowEl, opts);

        const btns = items.map((item, i) => {
          const el = document.createElement("button");
          el.className = "xbtn";
          applyStyleVars(el, item);
          const showIcon = item.show_icon !== undefined ? item.show_icon
            : item.show_icons !== undefined ? item.show_icons : this._config.show_icons;
          if (showIcon === false) el.classList.add("noicon");
          el.classList.add(`ind-${item.state_indicator || this._config.state_indicator || "background"}`);
          let icon;
          if (item.icon) {
            icon = document.createElement("ha-icon");
            icon.icon = item.icon;
          } else if (customElements.get("ha-state-icon")) {
            icon = document.createElement("ha-state-icon");
          } else {
            icon = document.createElement("ha-icon");
            icon.icon = DEFAULT_ICONS[item.entity.split(".")[0]] || "mdi:help-circle-outline";
          }
          const n = document.createElement("span");
          n.className = "n";
          const s = document.createElement("span");
          s.className = "s";
          icon.classList.add("ic");
          el.append(icon, n, s);
          this._attachPress(el, item, `${r}-${i}`);
          rowEl.append(el);
          return { item, el, icon, n, s, key: `${r}-${i}` };
        });
        return { rowEl, opts, btns };
      });

      // Only offer modes the entity reports; re-checked on every render.
      this._modesEl.style.display = this._config.show_hvac_modes === true ? "" : "none";

      // Round power button, top right: off <-> the first non-off HVAC mode.
      const power = document.createElement("button");
      power.className = `power ind-${this._config.state_indicator || "background"}`;
      power.title = "Power";
      power.hidden = this._config.show_power_button === false;
      power.innerHTML = `<svg viewBox="0 0 24 24"><path fill="currentColor" d="${POWER_ICON}"></path></svg>`;
      power.addEventListener("click", () => this._togglePower());
      card.append(power);
      this._powerEl = power;
      this._modesEl.classList.add(`ind-${this._config.state_indicator || "background"}`);
    }

    _attachPress(el, item, key) {
      let timer = null;
      let longFired = false;
      const clear = () => { clearTimeout(timer); timer = null; };
      el.addEventListener("pointerdown", () => {
        longFired = false;
        clear();
        timer = setTimeout(() => { longFired = true; this._moreInfo(item.entity); }, LONG_PRESS_MS);
      });
      ["pointerup", "pointerleave", "pointercancel"].forEach((ev) => el.addEventListener(ev, clear));
      el.addEventListener("contextmenu", (ev) => { ev.preventDefault(); clear(); longFired = true; this._moreInfo(item.entity); });
      el.addEventListener("click", () => {
        if (longFired) { longFired = false; return; }
        this._tap(item, key);
      });
    }

    _moreInfo(entityId) {
      this.dispatchEvent(new CustomEvent("hass-more-info", { detail: { entityId }, bubbles: true, composed: true }));
    }

    _tap(item, key) {
      const st = this._hass.states[item.entity];
      if (!st || st.state === "unavailable") { this._moreInfo(item.entity); return; }
      const domain = item.entity.split(".")[0];
      if (TOGGLE_DOMAINS.includes(domain)) {
        this._hass.callService(domain, "toggle", { entity_id: item.entity });
      } else if (SELECT_DOMAINS.includes(domain)) {
        this._openSelect = this._openSelect === key ? null : key;
        this._renderRows();
      } else if (PRESS_DOMAINS.includes(domain)) {
        this._hass.callService(domain, "press", { entity_id: item.entity });
      } else {
        this._moreInfo(item.entity);
      }
    }

    /* ---------- render ---------- */

    _render() {
      super._render();
      const st = this._hass.states[this._config.entity];
      const modes = (st && st.attributes.hvac_modes) || [];
      for (const b of this._modeBtns) {
        b.el.hidden = modes.length > 0 && !modes.includes(b.mode);
        // Only light a mode that is actually running; a lit power button
        // while the heater is off reads as "on".
        if (b.mode === "off") b.el.setAttribute("aria-pressed", "false");
      }
      if (this._powerEl) {
        const unavailable = !st || st.state === "unavailable";
        const on = !unavailable && st.state !== "off" && st.state !== "unknown";
        this._powerEl.classList.toggle("on", on);
        this._powerEl.disabled = unavailable;
        this._powerEl.setAttribute("aria-pressed", String(on));
        if (this._powerBusyState !== undefined && st && st.state !== this._powerBusyState) {
          this._powerBusyState = undefined;
          this._powerEl.classList.remove("busy");
        }
      }
      this._renderRows();
    }

    _togglePower() {
      const st = this._hass.states[this._config.entity];
      if (!st || st.state === "unavailable") return;
      let mode = "off";
      if (st.state === "off" || st.state === "unknown") {
        const modes = (st.attributes.hvac_modes || []).filter((m) => m !== "off");
        mode = this._config.power_on_mode || (modes.includes("heat") ? "heat" : modes[0]);
        if (!mode) return;
      }
      // Dim until the panel confirms over BLE, so a tap visibly registered.
      this._powerBusyState = st.state;
      this._powerEl.classList.add("busy");
      clearTimeout(this._powerBusyTimer);
      this._powerBusyTimer = setTimeout(() => {
        this._powerBusyState = undefined;
        if (this._powerEl) this._powerEl.classList.remove("busy");
      }, 8000);
      this._hass.callService("climate", "set_hvac_mode", { entity_id: this._config.entity, hvac_mode: mode });
    }

    _renderRows() {
      if (!this._rowEls || !this._hass) return;
      for (const row of this._rowEls) {
        let openBtn = null;
        for (const b of row.btns) {
          const st = this._hass.states[b.item.entity];
          const domain = b.item.entity.split(".")[0];
          const unavailable = !st || st.state === "unavailable" || st.state === "unknown";
          const isSelect = SELECT_DOMAINS.includes(domain);
          // A select only lights when it has an "off" option and is not on it;
          // a choice like Electric/Gas has no off state, so it never lights.
          const hasOff = isSelect && st && (st.attributes.options || []).some((o) => String(o).toLowerCase() === "off");
          const active = !unavailable && (isSelect ? hasOff && st.state.toLowerCase() !== "off" : st.state === "on");

          b.n.textContent = b.item.name || this._shortName(b.item.entity, st);
          b.s.textContent = unavailable ? "Unavailable" : this._formatState(st, domain);
          b.el.classList.toggle("active", active);
          b.el.classList.toggle("unavailable", unavailable);
          b.el.classList.toggle("open", this._openSelect === b.key);
          if (b.icon.localName === "ha-state-icon") {
            b.icon.hass = this._hass;
            b.icon.stateObj = st;
          }
          if (this._openSelect === b.key && isSelect && !unavailable) openBtn = { b, st, domain };
        }

        row.opts.hidden = !openBtn;
        if (openBtn) {
          const { b, st, domain } = openBtn;
          const options = st.attributes.options || [];
          const sig = `${b.key}|${st.state}|${options.join(",")}`;
          if (row.opts.dataset.sig !== sig) {
            row.opts.dataset.sig = sig;
            row.opts.innerHTML = "";
            for (const opt of options) {
              const o = document.createElement("button");
              o.textContent = opt;
              o.classList.toggle("sel", opt === st.state);
              o.addEventListener("click", () => {
                this._hass.callService(domain, "select_option", { entity_id: b.item.entity, option: opt });
                this._openSelect = null;
                this._renderRows();
              });
              row.opts.append(o);
            }
          }
        } else {
          row.opts.dataset.sig = "";
        }
      }
    }

    // The entity's own name without its device's name in front:
    // "Alde Compact 3020 HE Electric heating" -> "Electric heating".
    // Names you set yourself that do not start with the device name
    // (e.g. "Gas Priority") are left as they are.
    _shortName(entityId, st) {
      const full = (st && st.attributes.friendly_name) || entityId;
      const reg = this._hass.entities && this._hass.entities[entityId];
      const dev = reg && reg.device_id && this._hass.devices && this._hass.devices[reg.device_id];
      const devNames = dev ? [dev.name_by_user, dev.name].filter(Boolean) : [];
      for (const d of devNames) {
        if (full.length > d.length && full.toLowerCase().startsWith(d.toLowerCase() + " ")) {
          const rest = full.slice(d.length + 1).trim();
          return rest.charAt(0).toUpperCase() + rest.slice(1);
        }
      }
      return full;
    }

    _formatState(st, domain) {
      if (this._hass.formatEntityState) {
        try { return this._hass.formatEntityState(st); } catch (e) { /* fall through */ }
      }
      if (domain === "switch" || domain === "input_boolean") return st.state === "on" ? "On" : "Off";
      return st.state;
    }
  }

  if (!customElements.get(TAG)) customElements.define(TAG, TrumaClimateDialCustomCard);
}

customElements.whenDefined("home-assistant").then(() =>
  customElements.whenDefined(BASE_TAG).then(define)
);

window.customCards = window.customCards || [];
window.customCards.push({
  type: TAG,
  name: "Truma climate dial (custom)",
  description:
    "Truma climate dial with HVAC mode buttons plus two rows of up to three switch/select buttons that share the card width.",
  preview: true,
});
