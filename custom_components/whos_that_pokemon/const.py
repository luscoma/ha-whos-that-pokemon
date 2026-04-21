"""Constants for the Who's That Pokémon integration."""
from __future__ import annotations

DOMAIN = "whos_that_pokemon"

CONF_GENERATION = "generation"
DEFAULT_GENERATION = 0

POKEAPI_BASE = "https://pokeapi.co/api/v2"

# Hardcoded ID ranges per mainline generation. Covers base species only —
# this matches the anime-style "Who's That Pokémon?" framing (no regional
# forms or megas). Updated as of Gen IX (Scarlet/Violet, 1-1025).
GENERATIONS: dict[int, dict] = {
    0: {"label": "All Generations", "low": 1, "high": 1025},
    1: {"label": "Generation I — Kanto", "low": 1, "high": 151},
    2: {"label": "Generation II — Johto", "low": 152, "high": 251},
    3: {"label": "Generation III — Hoenn", "low": 252, "high": 386},
    4: {"label": "Generation IV — Sinnoh", "low": 387, "high": 493},
    5: {"label": "Generation V — Unova", "low": 494, "high": 649},
    6: {"label": "Generation VI — Kalos", "low": 650, "high": 721},
    7: {"label": "Generation VII — Alola", "low": 722, "high": 809},
    8: {"label": "Generation VIII — Galar", "low": 810, "high": 905},
    9: {"label": "Generation IX — Paldea", "low": 906, "high": 1025},
}

# Frontend card bundled with the integration.
FRONTEND_SCRIPT_URL = "/whos_that_pokemon/whos-that-pokemon-card.js"
FRONTEND_SCRIPT_RELPATH = "frontend/whos-that-pokemon-card.js"
