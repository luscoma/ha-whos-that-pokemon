"""The Who's That Pokémon integration."""
from __future__ import annotations

import json
import logging
from pathlib import Path

from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import async_call_later

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

_FRONTEND_KEY = f"{DOMAIN}_card_registration"


def _manifest_version() -> str:
    """Read the integration version from manifest.json at import time."""
    try:
        manifest = json.loads((Path(__file__).parent / "manifest.json").read_text())
        return manifest.get("version", "0")
    except Exception:  # noqa: BLE001
        return "0"


class PokemonCardRegistration:
    """Handles Lovelace resource registration for the bundled card.

    Mirrors the pattern used by integrations like bambu_lab that need to
    register a frontend card across multiple HA versions.  The key points:

    - hass.data["lovelace"] changed shape across releases:
        < 2025.2   plain dict  — access via ["key"]
        2025.2+    object      — access via .attribute
        2026.2+    object      — mode attr renamed to resource_mode
    - The resource storage backend may not be loaded at integration startup;
      we poll every 5 s until resources.loaded is True.
    - We append ?v=<version> to bust browser caches after upgrades and update
      the stored URL in place rather than creating a duplicate entry.
    """

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass
        self._version = _manifest_version()

    # ------------------------------------------------------------------
    # Version-aware properties
    # ------------------------------------------------------------------

    @property
    def _lovelace(self):
        return self.hass.data.get("lovelace")

    @property
    def resource_mode(self) -> str | None:
        lv = self._lovelace
        if lv is None:
            return None
        if hasattr(lv, "resource_mode"):    # HA >= 2026.2
            return lv.resource_mode
        if hasattr(lv, "mode"):             # HA 2025.2 – 2026.1
            return lv.mode
        if isinstance(lv, dict):            # HA < 2025.2
            return lv.get("mode")
        return None

    @property
    def resources(self):
        lv = self._lovelace
        if lv is None:
            return None
        if hasattr(lv, "resources"):
            return lv.resources
        if isinstance(lv, dict):
            return lv.get("resources")
        return None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def async_register(self) -> None:
        await self._async_register_static_path()
        if self.resource_mode == "storage":
            await self._async_wait_for_resources()
        else:
            _LOGGER.info(
                "Lovelace is in YAML mode — add %s as a resource manually.",
                FRONTEND_SCRIPT_URL,
            )

    async def async_unregister(self) -> None:
        """Remove the resource record when the integration is unloaded."""
        resources = self.resources
        if resources is None or self.resource_mode != "storage":
            return
        for item in list(resources.async_items()):
            if item["url"].split("?")[0] == FRONTEND_SCRIPT_URL:
                await resources.async_delete_item(item["id"])
                _LOGGER.debug("Removed Lovelace resource %s", item["url"])

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _async_register_static_path(self) -> None:
        script_path = Path(__file__).parent / FRONTEND_SCRIPT_RELPATH
        if not script_path.is_file():
            _LOGGER.warning("Frontend script missing at %s", script_path)
            return
        try:
            await self.hass.http.async_register_static_paths(
                [StaticPathConfig(FRONTEND_SCRIPT_URL, str(script_path), cache_headers=True)]
            )
            _LOGGER.debug("Registered static path %s", FRONTEND_SCRIPT_URL)
        except RuntimeError:
            _LOGGER.debug("Static path %s already registered", FRONTEND_SCRIPT_URL)

    async def _async_wait_for_resources(self) -> None:
        """Poll until the Lovelace storage backend is ready, then register."""
        async def _check(now) -> None:
            resources = self.resources
            if resources is None:
                _LOGGER.debug("Lovelace resources unavailable, retrying in 5 s")
                async_call_later(self.hass, 5, _check)
                return
            if not resources.loaded:
                _LOGGER.debug("Lovelace resources not loaded yet, retrying in 5 s")
                async_call_later(self.hass, 5, _check)
                return
            await self._async_register_resource()

        await _check(None)

    async def _async_register_resource(self) -> None:
        resources = self.resources
        versioned_url = f"{FRONTEND_SCRIPT_URL}?v={self._version}"

        existing = [
            r for r in resources.async_items()
            if r["url"].split("?")[0] == FRONTEND_SCRIPT_URL
        ]

        if existing:
            item = existing[0]
            if item["url"] == versioned_url:
                _LOGGER.debug("Card already registered at %s", versioned_url)
            else:
                _LOGGER.debug(
                    "Updating card resource from %s to %s", item["url"], versioned_url
                )
                await resources.async_update_item(
                    item["id"], {"res_type": "module", "url": versioned_url}
                )
        else:
            _LOGGER.debug("Registering card resource at %s", versioned_url)
            await resources.async_create_item(
                {"res_type": "module", "url": versioned_url}
            )


# ------------------------------------------------------------------
# Config entry lifecycle
# ------------------------------------------------------------------

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

    # Only register the frontend once, even if multiple entries exist.
    if not hass.data.get(_FRONTEND_KEY):
        registration = PokemonCardRegistration(hass)
        hass.data[_FRONTEND_KEY] = registration
        await registration.async_register()

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_options_updated))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        coordinator: PokemonCoordinator = hass.data[DOMAIN].pop(entry.entry_id)
        await coordinator.async_shutdown()

        # Clean up the resource record if this was the last loaded entry.
        if not hass.data.get(DOMAIN):
            registration: PokemonCardRegistration = hass.data.pop(_FRONTEND_KEY, None)
            if registration:
                await registration.async_unregister()

    return unload_ok


async def _async_options_updated(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)
