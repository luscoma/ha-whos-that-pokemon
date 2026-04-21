"""The Who's That Pokémon integration."""
from __future__ import annotations

import logging
from pathlib import Path

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import (
    CONF_GENERATION,
    DEFAULT_GENERATION,
    DOMAIN,
    FRONTEND_SCRIPT_RELPATH,
    FRONTEND_SCRIPT_URL,
)
from .coordinator import PokemonCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]

_FRONTEND_KEY = f"{DOMAIN}_frontend_registered"


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    generation = int(
        entry.options.get(
            CONF_GENERATION, entry.data.get(CONF_GENERATION, DEFAULT_GENERATION)
        )
    )

    coordinator = PokemonCoordinator(hass, generation)
    await coordinator.async_config_entry_first_refresh()
    await coordinator.async_schedule_midnight_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await _async_register_frontend(hass)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(_async_options_updated))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        coordinator: PokemonCoordinator = hass.data[DOMAIN].pop(entry.entry_id)
        await coordinator.async_shutdown()
    return unload_ok


async def _async_options_updated(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def _async_register_frontend(hass: HomeAssistant) -> None:
    """Serve the bundled Lovelace card and auto-load it for all dashboards.

    This means the user does not need to manually add a Lovelace resource —
    installing the integration is enough to make `custom:whos-that-pokemon-card`
    available.
    """
    if hass.data.get(_FRONTEND_KEY):
        return

    script_path = Path(__file__).parent / FRONTEND_SCRIPT_RELPATH
    if not script_path.is_file():
        _LOGGER.warning("Frontend script missing at %s", script_path)
        return

    await hass.http.async_register_static_paths(
        [StaticPathConfig(FRONTEND_SCRIPT_URL, str(script_path), False)]
    )
    add_extra_js_url(hass, FRONTEND_SCRIPT_URL)
    hass.data[_FRONTEND_KEY] = True
    _LOGGER.info("Registered Who's That Pokémon card at %s", FRONTEND_SCRIPT_URL)
