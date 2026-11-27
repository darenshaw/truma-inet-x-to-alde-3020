# Timers (heating and hot water)

[← README](../README.md)

The integration includes six timers that Home Assistant runs itself. Each timer
can switch the room heating, the hot water, or both, on a daily, weekday or
weekend schedule.

They are separate from the panel's own timer slots (**Timer *n*** and **Timer
*n* schedule** on the panel device). Those can only be armed and disarmed from
Home Assistant: the panel describes each timer's settings as read-only (`perm`
0), and the settings it publishes hold a label, a start, an end and weekdays,
but no temperature. The "20 °C" a panel timer shows is its name, not a setting.

> **Keep the panel's own timer switches off** if you use these timers, so the
> two don't fight over the heating.

## Where they are

Settings → Devices & services → **Truma iNet X** → **iNet X Timers**.

All six timers are on this one device, under the panel, so the device list
grows by one entry instead of six:

```
Truma iNetX-AC4C1E            (the panel)
├─ Alde Compact 3020 HE
├─ Bluetooth management
└─ iNet X Timers              ← all six timers
```

## Entities

Each timer *n* (1 to 6) has six entities, 36 in all:

| Entity | Entity id | Type | What it does |
|---|---|---|---|
| **Timer *n* enabled** | `switch.timer_n_enabled` | Switch | Turns the timer on or off. A timer does nothing while it is off. |
| **Timer *n* controls** | `select.timer_n_controls` | Select | What the timer runs: **Heating**, **Hot water**, or **Heating and hot water**. State values: `heating`, `hot_water`, `heating_and_hot_water`. Default: Heating. |
| **Timer *n* start** | `time.timer_n_start` | Time | When the timer starts (hours and minutes). |
| **Timer *n* end** | `time.timer_n_end` | Time | When the timer ends. An end earlier than the start runs past midnight: 21:00 to 09:00 ends at 09:00 the next morning. A start equal to the end never runs, which is how a blank timer (00:00 to 00:00) stays inactive. |
| **Timer *n* temperature** | `number.timer_n_temperature` | Number, °C | The heating target while the timer runs, 5 to 30 °C in 1 °C steps. Default 20 °C. Not used for hot water. |
| **Timer *n* days** | `select.timer_n_days` | Select | **Every day**, **Weekdays** (Monday to Friday) or **Weekends** (Saturday and Sunday). State values: `every_day`, `weekdays`, `weekends`. These are the days the timer *starts* on, so a weekend timer from 22:00 to 06:00 still runs at 03:00 on Monday, having started on Sunday night. |

The entity ids shown are what a new installation gets. Like any entity, they
can be renamed in Home Assistant.

All settings are kept across restarts. The timer entities are always
available, even while the panel is out of range, so they can be edited at any
time.

## What a timer does

Heating and hot water are worked out separately, every minute:

**Heating** (timers set to *Heating* or *Heating and hot water*)

- At a timer's start, the climate entity is set to **Heat** at the timer's
  temperature.
- If heating timers overlap, the one that **started most recently** wins. A
  short timer inside a long one therefore works as a boost: 09:00–21:00 at
  20 °C with 17:00–19:00 at 23 °C gives 23 °C from 17:00, then 20 °C again
  from 19:00.
- At a timer's end, control passes to any other heating timer still running.
  If none is, the heating is turned **off**.

**Hot water** (timers set to *Hot water* or *Heating and hot water*)

- At a timer's start, the appliance's **Hot water** switch is turned on.
- At its end, the switch is turned off, unless another hot water timer is
  still running.
- A hot water timer never interrupts a heating timer, and the other way round.

**Other rules**

- A timer acts only when what should be running **changes**: at a start, at an
  end, or when you edit a timer so that a different timer (or a different
  temperature) applies now. A manual change to the heating in the middle of a
  timer therefore stays until the next start or end.
- Turning a timer on during its window applies it straight away.
- If a command fails, for example because the panel is out of Bluetooth range,
  it is retried every minute until it succeeds. A warning is logged once.
- After a restart, a timer whose window is running is applied again.
- The timers use Home Assistant's time zone and clock, not the panel's.

Which entities are driven:

| Target | Entity | Found by |
|---|---|---|
| Heating | the integration's climate entity (e.g. *Alde Compact 3020 HE*) | the climate entity of this integration that offers *Heat* |
| Hot water | the appliance's **Hot water** switch | `WaterHeating.Active` on the appliance |

If the vehicle has no hot water switch (a Truma Combi has a *Water heating*
select instead), hot water timers do nothing.

## Examples

**Warm by day, frost protection at night** (the panel's old settings on the
test van):

| Timer | Controls | Start | End | Temperature | Days |
|---|---|---|---|---|---|
| 1 | Heating | 09:00 | 21:00 | 20 °C | Every day |
| 5 | Heating | 21:00 | 09:00 | 11 °C | Every day |

**Hot water for the morning shower on weekdays:**

| Timer | Controls | Start | End | Days |
|---|---|---|---|---|
| 2 | Hot water | 06:30 | 08:00 | Weekdays |

## Dashboard

Any card can show the timer entities. A simple **Entities** card per timer:

```yaml
type: entities
title: Timer 1
entities:
  - entity: switch.timer_1_enabled
    name: Enabled
  - entity: select.timer_1_controls
    name: Controls
  - entity: time.timer_1_start
    name: Start
  - entity: time.timer_1_end
    name: End
  - entity: number.timer_1_temperature
    name: Temperature
  - entity: select.timer_1_days
    name: Days
```

The time rows show an inline time picker, the number a box and the selects a
drop-down, so everything can be changed on the card.

With [Bubble Card](https://github.com/Clooos/Bubble-Card) installed, a list of
six buttons that each show the timer's **On**/**Off** state and open that
timer's own pop-up works well on a tablet:

```yaml
# In the list pop-up (or anywhere on the view): one button per timer
type: custom:bubble-card
card_type: button
button_type: state
entity: switch.timer_1_enabled
name: Timer 1
icon: mdi:timer-outline
show_state: true
button_action:
  tap_action:
    action: navigate
    navigation_path: "#timer-1"
---
# The timer's own pop-up, holding the entities card above
type: custom:bubble-card
card_type: pop-up
hash: "#timer-1"
name: Timer 1
icon: mdi:timer-outline
cards:
  - type: entities
    entities:
      - switch.timer_1_enabled
      - select.timer_1_controls
      - time.timer_1_start
      - time.timer_1_end
      - number.timer_1_temperature
      - select.timer_1_days
```

## Automations

The timer entities are ordinary entities, so automations can change them, for
example to turn every timer off when leaving the van:

```yaml
action: switch.turn_off
target:
  entity_id:
    - switch.timer_1_enabled
    - switch.timer_2_enabled
    - switch.timer_3_enabled
    - switch.timer_4_enabled
    - switch.timer_5_enabled
    - switch.timer_6_enabled
```

## Limitations

- Home Assistant has to be running, and able to reach the panel, at a start or
  end for the change to happen. A missed command is retried every minute.
- Days are limited to every day, weekdays or weekends.
- The panel's display does not show these timers. It shows its own.
