"""Sensor platform exposing the Pokémon of the day."""
from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import PokemonCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: PokemonCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([PokemonOfTheDaySensor(coordinator, entry)])


class PokemonOfTheDaySensor(CoordinatorEntity[PokemonCoordinator], SensorEntity):
    """State = display name; attributes carry the rest."""

    _attr_icon = "mdi:pokeball"
    _attr_has_entity_name = True

    def __init__(self, coordinator: PokemonCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_pokemon_of_the_day"
        self._attr_name = "Pokémon of the Day"

    @property
    def native_value(self) -> str | None:
        data = self.coordinator.data
        return data.get("display_name") if data else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        data = self.coordinator.data or {}
        return {
            "id": data.get("id"),
            "slug": data.get("name"),
            "types": data.get("types"),
            "abilities": data.get("abilities"),
            "hidden_abilities": data.get("hidden_abilities"),
            "height_m": data.get("height_m"),
            "weight_kg": data.get("weight_kg"),
            "genus": data.get("genus"),
            "sprite": data.get("sprite"),
            "sprite_front": data.get("sprite_front"),
            "date": data.get("date"),
            "generation": data.get("generation"),
            "generation_label": data.get("generation_label"),
        }
