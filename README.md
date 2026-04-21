<p align="center">
  <img src="brand/icon.svg" width="140" alt="Who's That Pokémon? pokeball icon">
</p>

# Who's That Pokémon? — Home Assistant integration

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![GitHub release](https://img.shields.io/github/v/release/luscoma/ha-whos-that-pokemon?display_name=tag&sort=semver)](https://github.com/luscoma/ha-whos-that-pokemon/releases)

A custom Home Assistant integration + Lovelace card that picks a Pokémon every
day, shows it as a silhouette, and reveals it on tap. Inspired by
[sriniketh/trmnl-plugin-whos-that-pokemon](https://github.com/sriniketh/trmnl-plugin-whos-that-pokemon).

- **Deterministic daily pick** — same Pokémon for everyone on the same date
- **Generation / region filter** — all, or any of Gen I–IX
- **Silhouette + tap-to-reveal** with an anime-style flash animation
- **Responsive layouts** — quadrant, half, and full, auto-selected by the card's size
- **Persistent daily state** — once revealed, it stays revealed until tomorrow
- **Bundled Lovelace card** — auto-registered, no manual `resources:` edit needed
- Powered by [PokéAPI](https://pokeapi.co)

## Install (via HACS)

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=luscoma&repository=ha-whos-that-pokemon&category=integration)

Click the button above to add this repo to HACS in one step, or do it manually:

1. In HACS, add this repo as a **Custom Repository** (category: *Integration*).
2. Install **Who's That Pokémon?** from the integration list.
3. Restart Home Assistant.
4. Go to **Settings → Devices & Services → Add Integration** and pick
   **Who's That Pokémon?**. Choose the generation you want to draw from.

That's it — the integration both creates the `sensor.pokemon_of_the_day`
entity *and* serves the Lovelace card. You do not need to add a Lovelace
resource manually.

## Add the card to a dashboard

Edit any dashboard → **Add Card** → find *Who's That Pokémon?* in the custom
section, or drop this YAML in:

```yaml
type: custom:whos-that-pokemon-card
entity: sensor.pokemon_of_the_day
# optional:
question: Who's that Pokémon?
layout: auto         # auto | quadrant | half | full
```

Tap the silhouette to reveal. The reveal persists for the rest of the day
(per browser, per entity) and resets automatically at local midnight.

### Layouts

The card has three layouts that mirror the original TRMNL plugin. By default
it picks one based on the card's rendered width (via CSS container queries),
so dropping it into any grid spot Just Works. You can also lock a layout via
the `layout` option.

| Layout   | Width range     | Content                                                   |
|----------|-----------------|-----------------------------------------------------------|
| quadrant | &lt; 320 px        | Just the art + title bar. Perfect for a 1×1 grid tile.    |
| half     | 320 – 719 px    | Art + Name / Type / Species / Height / Weight.            |
| full     | ≥ 720 px        | Everything, including Abilities.                          |

## Configuration

All configuration happens in the UI. Re-open the integration from **Settings
→ Devices & Services** to change the generation filter.

| Generation | Region  | Dex range  |
|-----------:|---------|-----------:|
|        all | —       |   1 – 1025 |
|          1 | Kanto   |    1 – 151 |
|          2 | Johto   |  152 – 251 |
|          3 | Hoenn   |  252 – 386 |
|          4 | Sinnoh  |  387 – 493 |
|          5 | Unova   |  494 – 649 |
|          6 | Kalos   |  650 – 721 |
|          7 | Alola   |  722 – 809 |
|          8 | Galar   |  810 – 905 |
|          9 | Paldea  |  906 – 1025 |

## Exposed entity

`sensor.pokemon_of_the_day`

| Field                 | Description                                        |
|-----------------------|----------------------------------------------------|
| state                 | Display name, e.g. `Charizard`                     |
| `id`                  | National Dex number                                |
| `slug`                | PokéAPI slug (e.g. `mr-mime`)                      |
| `types`               | List of type slugs                                 |
| `abilities`           | Non-hidden abilities (prettified)                  |
| `hidden_abilities`    | Hidden abilities (prettified)                      |
| `height_m`, `weight_kg` | Numeric, SI units                                |
| `genus`               | English species genus (e.g. `Flame Pokémon`)       |
| `sprite`              | Official artwork URL                               |
| `sprite_front`        | Gen-1 style front sprite (fallback)                |
| `date`                | ISO date the pick was made for                     |
| `generation`          | Configured generation id                           |
| `generation_label`    | Friendly generation label                          |

You can use any of this in automations — announce the Pokémon on a speaker
in the morning, mirror it onto an e-ink display, whatever you want.

## How the daily pick works

`sha256(today.isoformat())` seeds a deterministic index into the configured
generation's ID range. Same date → same Pokémon, on every install, forever.
A midnight listener (`async_track_time_change` at 00:00:05 local) refreshes
the coordinator when the day rolls over even if no one opens the dashboard.

## Dev notes

- Integration domain: `whos_that_pokemon`
- Frontend card is served from the integration package at
  `/whos_that_pokemon/whos-that-pokemon-card.js` and auto-added to all
  dashboards via `add_extra_js_url`.
- No external Python dependencies — just `aiohttp` through HA's shared client
  session.
