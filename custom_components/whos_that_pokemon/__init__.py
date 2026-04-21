"""The Who's That Pokémon integration."""
from __future__ import annotations

import logging
from pathlib import Path

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.components.lovelace.resources import ResourceStorageCollection
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
    """Serve the bundled Lovelace card and register it so it loads before rendering.

    Strategy (in priority order):
    1. Lovelace resource storage — the card is stored as a proper dashboard
       resource, which HA loads in the document <head> before Lovelace renders.
       This avoids the race condition where add_extra_js_url's async module
       loads after HA's 2-second customElements timeout fires.
    2. add_extra_js_url — fallback for YAML-mode dashboards where the
       ResourceStorageCollection is not available.
    """
    if hass.data.get(_FRONTEND_KEY):
        return

    script_path = Path(__file__).parent / FRONTEND_SCRIPT_RELPATH
    if not script_path.is_file():
        _LOGGER.warning("Frontend script missing at %s", script_path)
        return

    await hass.http.async_register_static_paths(
        [StaticPathConfig(FRONTEND_SCRIPT_URL, str(script_path), cache_headers=True)]
    )

    if not await _async_register_lovelace_resource(hass, FRONTEND_SCRIPT_URL):
        # YAML-mode dashboards: fall back to extra JS injection.
        add_extra_js_url(hass, FRONTEND_SCRIPT_URL)
        _LOGGER.debug(
            "Lovelace storage unavailable; registered card via add_extra_js_url. "
            "If the card fails to load, add %s as a Lovelace resource manually.",
            FRONTEND_SCRIPT_URL,
        )

    hass.data[_FRONTEND_KEY] = True
    _LOGGER.info("Registered Who's That Pokémon card at %s", FRONTEND_SCRIPT_URL)


async def _async_register_lovelace_resource(hass: HomeAssistant, url: str) -> bool:
    """Register url in the Lovelace resource storage collection.

    Returns True if the resource was registered (or already present),
    False if the storage backend is unavailable (YAML-mode dashboards).
    """
    try:
        lovelace = hass.data.get("lovelace")
        if not lovelace:
            return False
        resources = lovelace.get("resources")
        if not isinstance(resources, ResourceStorageCollection):
            return False

        # Load existing resources so async_items() is populated.
        await resources.async_load()

        if any(item["url"] == url for item in resources.async_items()):
            _LOGGER.debug("Lovelace resource %s already registered", url)
            return True

        await resources.async_create_item({"res_type": "module", "url": url})
        _LOGGER.debug("Registered Lovelace resource %s", url)
        return True
    except Exception as err:  # noqa: BLE001
        _LOGGER.debug("Could not register Lovelace resource: %s", err)
        return False
