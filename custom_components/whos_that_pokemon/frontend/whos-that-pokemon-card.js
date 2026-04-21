/*!
 * Who's That Pokémon? — Home Assistant Lovelace card
 * Bundled with the whos_that_pokemon integration.
 */

const TYPE_COLORS = {
  normal: "#A8A77A", fire: "#EE8130", water: "#6390F0", electric: "#F7D02C",
  grass: "#7AC74C", ice: "#96D9D6", fighting: "#C22E28", poison: "#A33EA1",
  ground: "#E2BF65", flying: "#A98FF3", psychic: "#F95587", bug: "#A6B91A",
  rock: "#B6A136", ghost: "#735797", dragon: "#6F35FC", dark: "#705746",
  steel: "#B7B7CE", fairy: "#D685AD",
};

const DEFAULT_QUESTION = "Who's that Pokémon?";
const LAYOUTS = ["auto", "quadrant", "half", "full"];
const CARD_VERSION = "0.2.1";

class WhosThatPokemonCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._renderedOnce = false;
    this._lastSpriteUrl = null;
  }

  setConfig(config) {
    if (!config || !config.entity) {
      throw new Error("You need to define an entity (e.g. sensor.pokemon_of_the_day)");
    }
    const layout = LAYOUTS.includes(config.layout) ? config.layout : "auto";
    this._config = { ...config, layout };
    this._renderSkeleton();
    this._applyLayout();
    this._update();
  }

  set hass(hass) {
    this._hass = hass;
    this._update();
  }

  // Hint to HA's layout engine about how tall this card wants to be.
  // Scales down for compact layouts so grid placement behaves sensibly.
  getCardSize() {
    const layout = this._config?.layout || "auto";
    if (layout === "quadrant") return 2;
    if (layout === "half") return 3;
    return 5;
  }

  getLayoutOptions() {
    const layout = this._config?.layout || "auto";
    if (layout === "quadrant") {
      return { grid_columns: 2, grid_rows: 2, grid_min_columns: 2, grid_min_rows: 2 };
    }
    if (layout === "half") {
      return { grid_columns: 4, grid_rows: 3, grid_min_columns: 3, grid_min_rows: 2 };
    }
    if (layout === "full") {
      return { grid_columns: 12, grid_rows: 4, grid_min_columns: 6, grid_min_rows: 3 };
    }
    // auto: let HA pick, but set sensible minimum
    return { grid_min_columns: 2, grid_min_rows: 2 };
  }

  static getStubConfig(hass) {
    const match = Object.keys(hass?.states || {}).find(
      (id) => id.startsWith("sensor.") && id.includes("pokemon_of_the_day"),
    );
    return { entity: match || "sensor.pokemon_of_the_day", layout: "auto" };
  }

  static getConfigElement() {
    return document.createElement("whos-that-pokemon-card-editor");
  }

  _renderSkeleton() {
    if (this._renderedOnce) return;
    this.shadowRoot.innerHTML = `
      <style>${this._css()}</style>
      <ha-card>
        <div class="wrap" data-layout="auto">
          <div class="art-col">
            <div class="art-frame" part="art-frame">
              <img class="art" alt="" draggable="false" />
              <div class="flash"></div>
              <div class="tap-hint">Tap to reveal</div>
            </div>
            <div class="title-bar">
              <svg class="pokeball" viewBox="0 0 32 32" aria-hidden="true">
                <circle cx="16" cy="16" r="14" fill="#fff" stroke="currentColor" stroke-width="2"/>
                <path d="M2 16 a14 14 0 0 1 28 0" fill="currentColor" opacity="0.9"/>
                <path d="M2 16 h28" stroke="currentColor" stroke-width="2" fill="none"/>
                <circle cx="16" cy="16" r="4" fill="#fff" stroke="currentColor" stroke-width="2"/>
                <circle cx="16" cy="16" r="1.5" fill="currentColor"/>
              </svg>
              <span class="headline"></span>
              <span class="pid"></span>
            </div>
          </div>
          <div class="stats-col"></div>
        </div>
      </ha-card>
    `;
    this.shadowRoot
      .querySelector(".art-frame")
      .addEventListener("click", () => this._toggleReveal());
    this._renderedOnce = true;
  }

  _applyLayout() {
    const wrap = this.shadowRoot?.querySelector(".wrap");
    if (!wrap || !this._config) return;
    wrap.dataset.layout = this._config.layout;
  }

  _css() {
    // Layout rules:
    //   • `auto` is driven by @container queries (see `.wrap[data-layout="auto"]` blocks)
    //   • `quadrant`, `half`, `full` force a specific layout regardless of width
    //   • stat priorities:
    //       .stat.high  → Name + Type (always shown when stats show)
    //       .stat.mid   → Species, Height, Weight (shown from half upward)
    //       .stat.low   → Abilities (full only)
    return `
      :host { display: block; }
      ha-card {
        padding: 14px;
        overflow: hidden;
        height: 100%;
        box-sizing: border-box;
      }

      .wrap {
        container-type: inline-size;
        display: grid;
        grid-template-columns: 1fr;
        gap: 12px;
        height: 100%;
      }

      .art-col {
        display: flex;
        flex-direction: column;
        gap: 10px;
        min-width: 0;
      }

      .art-frame {
        position: relative;
        aspect-ratio: 1 / 1;
        background: var(--secondary-background-color, #e7e7ea);
        border-radius: 14px;
        display: flex;
        align-items: center;
        justify-content: center;
        cursor: pointer;
        overflow: hidden;
        user-select: none;
        flex: 1 1 auto;
        min-height: 0;
      }
      .art {
        max-width: 88%;
        max-height: 88%;
        object-fit: contain;
        filter: brightness(0) contrast(100%);
        transition: filter 600ms ease-out;
        -webkit-user-drag: none;
      }
      .revealed .art { filter: none; }

      .flash {
        position: absolute; inset: 0;
        background: #fff;
        opacity: 0;
        pointer-events: none;
      }
      .revealing .flash { animation: wtp-flash 520ms ease-out; }
      @keyframes wtp-flash {
        0%   { opacity: 0; }
        35%  { opacity: 0.95; }
        100% { opacity: 0; }
      }

      .tap-hint {
        position: absolute;
        bottom: 6px;
        right: 10px;
        font-size: 0.65rem;
        letter-spacing: 0.05em;
        text-transform: uppercase;
        opacity: 0.5;
        pointer-events: none;
        transition: opacity 300ms ease-out;
      }
      .revealed .tap-hint { opacity: 0; }

      .title-bar {
        display: flex;
        align-items: center;
        gap: 8px;
        padding: 6px 10px;
        background: var(--primary-color);
        color: var(--text-primary-color, #fff);
        border-radius: 10px;
        font-weight: 600;
        font-size: 0.9rem;
      }
      .pokeball { width: 20px; height: 20px; flex: 0 0 auto; }
      .headline {
        flex: 1;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }
      .pid {
        opacity: 0.85;
        font-variant-numeric: tabular-nums;
        font-size: 0.85em;
      }

      /* Stats column — hidden at quadrant, shown/arranged by layout rules below */
      .stats-col {
        display: none;
        min-width: 0;
      }
      .stat { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
      .stat.mid, .stat.low { display: none; }
      .stat .label {
        font-size: 0.68rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        opacity: 0.6;
      }
      .stat .value {
        font-size: 0.95rem;
        font-weight: 500;
        word-break: break-word;
        transition: filter 500ms ease-out;
      }
      .wrap:not(.revealed) .stat.blur .value { filter: blur(7px); }

      .types { display: flex; gap: 6px; flex-wrap: wrap; align-items: center; }
      .type-chip {
        padding: 2px 8px;
        border-radius: 999px;
        font-size: 0.68rem;
        font-weight: 700;
        text-transform: uppercase;
        color: #fff;
        letter-spacing: 0.05em;
        white-space: nowrap;
      }

      .error {
        padding: 8px;
        color: var(--error-color, #b00);
        font-size: 0.9rem;
      }

      /* =============== AUTO LAYOUT (container queries) =============== */
      /* Default (below 320px): quadrant — only art + title bar visible. */

      /* Half-V: single column, stats row below art */
      @container (min-width: 320px) {
        .wrap[data-layout="auto"] .stats-col {
          display: flex;
          flex-direction: row;
          flex-wrap: wrap;
          gap: 10px 16px;
        }
        .wrap[data-layout="auto"] .stat { flex: 1 1 120px; }
      }

      /* Half-H: two columns side by side */
      @container (min-width: 480px) {
        .wrap[data-layout="auto"] {
          grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
          align-items: stretch;
        }
        .wrap[data-layout="auto"] .stats-col {
          flex-direction: column;
          flex-wrap: nowrap;
          justify-content: space-around;
          gap: 8px;
        }
        .wrap[data-layout="auto"] .stat.mid { display: flex; }
      }

      /* Full: add abilities row + a bit more breathing room */
      @container (min-width: 720px) {
        .wrap[data-layout="auto"] { gap: 16px; }
        .wrap[data-layout="auto"] .stat.low { display: flex; }
        .wrap[data-layout="auto"] .title-bar { font-size: 1rem; padding: 8px 12px; }
        .wrap[data-layout="auto"] .pokeball { width: 22px; height: 22px; }
        .wrap[data-layout="auto"] .stat .value { font-size: 1rem; }
      }

      /* =============== FORCED LAYOUTS =============== */
      /* Quadrant: no stats, ever. */
      .wrap[data-layout="quadrant"] .stats-col { display: none; }

      /* Half: side-by-side, mid stats on, abilities off. */
      .wrap[data-layout="half"] {
        grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
        align-items: stretch;
      }
      .wrap[data-layout="half"] .stats-col {
        display: flex;
        flex-direction: column;
        justify-content: space-around;
        gap: 8px;
      }
      .wrap[data-layout="half"] .stat.mid { display: flex; }

      /* Full: everything. */
      .wrap[data-layout="full"] {
        grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
        align-items: stretch;
        gap: 16px;
      }
      .wrap[data-layout="full"] .stats-col {
        display: flex;
        flex-direction: column;
        justify-content: space-around;
        gap: 10px;
      }
      .wrap[data-layout="full"] .stat.mid,
      .wrap[data-layout="full"] .stat.low { display: flex; }
      .wrap[data-layout="full"] .title-bar { font-size: 1rem; padding: 8px 12px; }
      .wrap[data-layout="full"] .pokeball { width: 22px; height: 22px; }
      .wrap[data-layout="full"] .stat .value { font-size: 1rem; }
    `;
  }

  _update() {
    if (!this._hass || !this._config) return;
    const stateObj = this._hass.states[this._config.entity];
    const root = this.shadowRoot;
    const wrap = root.querySelector(".wrap");
    const statsCol = root.querySelector(".stats-col");
    const titleBar = root.querySelector(".title-bar");
    const headline = root.querySelector(".headline");
    const pid = root.querySelector(".pid");
    const art = root.querySelector(".art");
    const frame = root.querySelector(".art-frame");

    if (!stateObj) {
      statsCol.innerHTML = `<div class="error">Entity <code>${this._config.entity}</code> not found.</div>`;
      statsCol.style.display = "block";
      titleBar.style.display = "none";
      return;
    }
    titleBar.style.display = "";
    statsCol.style.display = "";

    // Re-apply layout in case config changed without a full skeleton re-render.
    wrap.dataset.layout = this._config.layout;

    const attrs = stateObj.attributes || {};
    const today = attrs.date || new Date().toISOString().slice(0, 10);
    const storageKey = `wtp-revealed-${this._config.entity}`;
    const revealed = localStorage.getItem(storageKey) === today;

    this._today = today;
    this._storageKey = storageKey;

    // Sprite: only reassign when it actually changes, so the silhouette
    // animation doesn't retrigger on unrelated state updates.
    const sprite = attrs.sprite || attrs.sprite_front || "";
    if (sprite && sprite !== this._lastSpriteUrl) {
      art.src = sprite;
      art.alt = stateObj.state || "Pokémon";
      this._lastSpriteUrl = sprite;
    }

    pid.textContent = attrs.id ? `#${String(attrs.id).padStart(4, "0")}` : "";
    headline.textContent = revealed
      ? `It's ${stateObj.state}!`
      : this._config.question || DEFAULT_QUESTION;

    frame.classList.toggle("revealed", revealed);
    wrap.classList.toggle("revealed", revealed);

    statsCol.innerHTML = this._renderStats(stateObj, attrs, revealed);
  }

  _renderStats(stateObj, attrs, revealed) {
    const chips = (attrs.types || [])
      .map(
        (t) =>
          `<span class="type-chip" style="background:${TYPE_COLORS[t] || "#777"}">${t}</span>`,
      )
      .join("");

    const fmtHeight = attrs.height_m != null ? `${attrs.height_m} m` : "—";
    const fmtWeight = attrs.weight_kg != null ? `${attrs.weight_kg} kg` : "—";
    const abilities = (attrs.abilities || []).join(", ") || "—";
    const name = revealed ? (stateObj.state || "—") : "???";

    // Priority classes control which stats appear at which layout tier:
    //   high → always (when stats column is visible at all)
    //   mid  → half + full
    //   low  → full only
    return `
      <div class="stat high"><div class="label">Name</div><div class="value">${name}</div></div>
      <div class="stat high blur"><div class="label">Type</div><div class="value types">${chips || "—"}</div></div>
      <div class="stat mid blur"><div class="label">Species</div><div class="value">${attrs.genus || "—"}</div></div>
      <div class="stat mid blur"><div class="label">Height</div><div class="value">${fmtHeight}</div></div>
      <div class="stat mid blur"><div class="label">Weight</div><div class="value">${fmtWeight}</div></div>
      <div class="stat low blur"><div class="label">Abilities</div><div class="value">${abilities}</div></div>
    `;
  }

  _toggleReveal() {
    if (!this._hass || !this._config) return;
    const root = this.shadowRoot;
    const frame = root.querySelector(".art-frame");
    if (frame.classList.contains("revealed")) return;

    frame.classList.add("revealing");
    setTimeout(() => frame.classList.remove("revealing"), 550);

    try {
      localStorage.setItem(this._storageKey, this._today);
    } catch (_e) {
      /* localStorage may be unavailable (private mode) — reveal still works until reload */
    }
    this._update();
  }
}

customElements.define("whos-that-pokemon-card", WhosThatPokemonCard);

/* --------------------- config editor --------------------- */

class WhosThatPokemonCardEditor extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
  }

  setConfig(config) {
    this._config = { ...config };
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  _render() {
    if (!this._hass) return;
    const entities = Object.keys(this._hass.states)
      .filter((id) => id.startsWith("sensor."))
      .sort();
    const currentEntity = this._config?.entity || "";
    const currentQuestion = this._config?.question || "";
    const currentLayout = LAYOUTS.includes(this._config?.layout)
      ? this._config.layout
      : "auto";

    this.shadowRoot.innerHTML = `
      <style>
        .row { display: flex; flex-direction: column; gap: 4px; margin: 10px 0; }
        label { font-size: 0.85rem; opacity: 0.75; }
        select, input {
          padding: 8px;
          font-size: 1rem;
          border-radius: 6px;
          border: 1px solid var(--divider-color, #ccc);
          background: var(--card-background-color, #fff);
          color: var(--primary-text-color, #000);
        }
        .hint { font-size: 0.75rem; opacity: 0.6; }
      </style>
      <div class="row">
        <label for="ent">Entity (required)</label>
        <select id="ent">
          ${entities
            .map(
              (e) =>
                `<option value="${e}"${e === currentEntity ? " selected" : ""}>${e}</option>`,
            )
            .join("")}
        </select>
        <div class="hint">Provided by the Who's That Pokémon? integration.</div>
      </div>
      <div class="row">
        <label for="layout">Layout</label>
        <select id="layout">
          <option value="auto"${currentLayout === "auto" ? " selected" : ""}>Auto (responsive)</option>
          <option value="quadrant"${currentLayout === "quadrant" ? " selected" : ""}>Quadrant — art only</option>
          <option value="half"${currentLayout === "half" ? " selected" : ""}>Half — art + key stats</option>
          <option value="full"${currentLayout === "full" ? " selected" : ""}>Full — everything</option>
        </select>
        <div class="hint">Auto picks a layout based on the card's rendered width.</div>
      </div>
      <div class="row">
        <label for="q">Headline (optional)</label>
        <input id="q" type="text" value="${currentQuestion.replace(/"/g, "&quot;")}" placeholder="${DEFAULT_QUESTION}" />
      </div>
    `;
    this.shadowRoot.getElementById("ent").addEventListener("change", (e) =>
      this._emit("entity", e.target.value),
    );
    this.shadowRoot.getElementById("layout").addEventListener("change", (e) =>
      this._emit("layout", e.target.value),
    );
    this.shadowRoot.getElementById("q").addEventListener("input", (e) =>
      this._emit("question", e.target.value),
    );
  }

  _emit(key, value) {
    this._config = { ...this._config, [key]: value };
    this.dispatchEvent(
      new CustomEvent("config-changed", {
        detail: { config: this._config },
        bubbles: true,
        composed: true,
      }),
    );
  }
}

customElements.define(
  "whos-that-pokemon-card-editor",
  WhosThatPokemonCardEditor,
);

/* --------------------- card picker registration --------------------- */

window.customCards = window.customCards || [];
if (!window.customCards.find((c) => c.type === "whos-that-pokemon-card")) {
  window.customCards.push({
    type: "whos-that-pokemon-card",
    name: "Who's That Pokémon?",
    description: "Daily Pokémon silhouette that reveals on tap.",
    preview: true,
  });
}

// Surface version in devtools for debugging.
console.info(
  `%c WHOS-THAT-POKEMON-CARD %c ${CARD_VERSION} `,
  "color: white; background: #cc0000; font-weight: 700;",
  "color: #cc0000; background: white; font-weight: 700;",
);
