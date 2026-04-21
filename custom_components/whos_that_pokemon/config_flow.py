"""Config flow for the Who's That Pokémon integration."""
from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .const import CONF_GENERATION, DEFAULT_GENERATION, DOMAIN, GENERATIONS


def _generation_selector() -> SelectSelector:
    options = [
        SelectOptionDict(value=str(gen_id), label=meta["label"])
        for gen_id, meta in GENERATIONS.items()
    ]
    return SelectSelector(
        SelectSelectorConfig(options=options, mode=SelectSelectorMode.DROPDOWN)
    )


class WhosThatPokemonConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Who's That Pokémon."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()

        if user_input is not None:
            return self.async_create_entry(
                title="Who's That Pokémon?",
                data={CONF_GENERATION: int(user_input[CONF_GENERATION])},
            )

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_GENERATION, default=str(DEFAULT_GENERATION)
                ): _generation_selector()
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema)

    @staticmethod
    @callback
    def async_get_options_flow(entry: ConfigEntry) -> OptionsFlow:
        return WhosThatPokemonOptionsFlow(entry)


class WhosThatPokemonOptionsFlow(OptionsFlow):
    """Allow changing the generation filter after install."""

    def __init__(self, entry: ConfigEntry) -> None:
        self._entry = entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(
                title="",
                data={CONF_GENERATION: int(user_input[CONF_GENERATION])},
            )

        current = self._entry.options.get(
            CONF_GENERATION,
            self._entry.data.get(CONF_GENERATION, DEFAULT_GENERATION),
        )
        schema = vol.Schema(
            {
                vol.Required(
                    CONF_GENERATION, default=str(current)
                ): _generation_selector()
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
