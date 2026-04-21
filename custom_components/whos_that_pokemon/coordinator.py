"""Data coordinator for the Who's That Pokémon integration.

The coordinator picks a Pokémon deterministically from the date + configured
generation range, fetches it from PokéAPI, and refreshes at local midnight so
the daily rotation happens even if nobody opens the dashboard.
"""
from __future__ import annotations

import hashlib
import logging
from datetime import date, datetime
from typing import Any

from homeassistant.core import CALLBACK_TYPE, HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.event import async_track_time_change
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, GENERATIONS, POKEAPI_BASE

_LOGGER = logging.getLogger(__name__)

REQUEST_TIMEOUT = 30


class PokemonCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Fetch the Pokémon of the day and expose normalised fields."""

    def __init__(self, hass: HomeAssistant, generation: int) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            # We don't use a fixed interval — refresh fires at local midnight
            # (see async_schedule_midnight_refresh) and on manual reload.
            update_interval=None,
        )
        self.generation = generation
        self._unsub_midnight: CALLBACK_TYPE | None = None

    async def _async_update_data(self) -> dict[str, Any]:
        gen = GENERATIONS.get(self.generation, GENERATIONS[0])
        today = datetime.now().date()
        pokedex_id = self._pick_for_date(today, gen["low"], gen["high"])

        session = async_get_clientsession(self.hass)
        try:
            async with session.get(
                f"{POKEAPI_BASE}/pokemon/{pokedex_id}", timeout=REQUEST_TIMEOUT
            ) as resp:
                resp.raise_for_status()
                pokemon = await resp.json()

            async with session.get(
                pokemon["species"]["url"], timeout=REQUEST_TIMEOUT
            ) as resp:
                resp.raise_for_status()
                species = await resp.json()
        except Exception as err:  # aiohttp + asyncio errors are varied
            raise UpdateFailed(f"PokéAPI request failed: {err}") from err

        genus = next(
            (
                g["genus"]
                for g in species.get("genera", [])
                if g.get("language", {}).get("name") == "en"
            ),
            None,
        )

        sprites = pokemon.get("sprites") or {}
        artwork = (
            (sprites.get("other") or {})
            .get("official-artwork", {})
            .get("front_default")
        )

        abilities = pokemon.get("abilities") or []
        return {
            "id": pokemon["id"],
            "name": pokemon["name"],
            "display_name": _prettify(pokemon["name"]),
            "types": [t["type"]["name"] for t in pokemon.get("types") or []],
            "abilities": [
                _prettify(a["ability"]["name"])
                for a in abilities
                if not a.get("is_hidden")
            ],
            "hidden_abilities": [
                _prettify(a["ability"]["name"])
                for a in abilities
                if a.get("is_hidden")
            ],
            "height_m": pokemon["height"] / 10,  # decimetres → metres
            "weight_kg": pokemon["weight"] / 10,  # hectograms → kilograms
            "genus": genus,
            "sprite": artwork,
            "sprite_front": sprites.get("front_default"),
            "date": today.isoformat(),
            "generation": self.generation,
            "generation_label": gen["label"],
        }

    @staticmethod
    def _pick_for_date(day: date, low: int, high: int) -> int:
        """Deterministic, well-distributed mapping from date → id in [low, high]."""
        digest = hashlib.sha256(day.isoformat().encode()).digest()
        span = high - low + 1
        return low + (int.from_bytes(digest[:8], "big") % span)

    async def async_schedule_midnight_refresh(self) -> None:
        """Trigger a refresh shortly after local midnight each day."""
        if self._unsub_midnight is not None:
            self._unsub_midnight()
        self._unsub_midnight = async_track_time_change(
            self.hass, self._handle_midnight, hour=0, minute=0, second=5
        )

    async def _handle_midnight(self, _now) -> None:
        await self.async_request_refresh()

    async def async_shutdown(self) -> None:
        if self._unsub_midnight is not None:
            self._unsub_midnight()
            self._unsub_midnight = None
        await super().async_shutdown()


def _prettify(slug: str) -> str:
    """'mr-mime' → 'Mr Mime'."""
    return slug.replace("-", " ").title()
