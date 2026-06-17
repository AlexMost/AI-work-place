import type { Game, Tile } from "./game";

export interface Elements {
  grid: HTMLElement; // background cell layer
  tiles: HTMLElement; // moving tile layer
  score: HTMLElement;
  best: HTMLElement;
  scoreBox: HTMLElement;
  overlay: HTMLElement;
  overlayTitle: HTMLElement;
  overlayActions: HTMLElement;
}

export function buildBackground(grid: HTMLElement, size: number): void {
  // --cell (in :root) is derived from --size, so it must live on an ancestor.
  document.documentElement.style.setProperty("--size", String(size));
  grid.innerHTML = "";
  for (let i = 0; i < size * size; i++) {
    const cell = document.createElement("div");
    cell.className = "cell";
    grid.appendChild(cell);
  }
}

/** Value classes cap out so we don't need an infinite palette. */
function valueClass(value: number): string {
  return `tile-${value <= 2048 ? value : "super"}`;
}

// Set transform inline (not via a custom prop in calc) so changing it actually
// triggers the CSS transition — that's what makes tiles slide by coordinate.
function position(el: HTMLElement, x: number, y: number): void {
  el.style.transform =
    `translate(calc((var(--cell) + var(--gap)) * ${x}),` +
    ` calc((var(--cell) + var(--gap)) * ${y}))`;
}

interface Mover {
  el: HTMLElement;
  x: number;
  y: number;
}

/**
 * Builds the elements for a tile (plus, for a merge, its two source tiles).
 * Tiles are placed at their *previous* position; any that need to travel are
 * collected in `movers` so the caller can slide them after a layout flush.
 */
function createTileEls(tile: Tile, movers: Mover[]): HTMLElement[] {
  const el = document.createElement("div");
  el.className = `tile ${valueClass(tile.value)}`;

  const inner = document.createElement("div");
  inner.className = "tile-inner";
  inner.textContent = String(tile.value);
  el.appendChild(inner);

  const from = tile.prev ?? { x: tile.x, y: tile.y };
  position(el, from.x, from.y);

  const els: HTMLElement[] = [el];

  if (tile.prev) {
    movers.push({ el, x: tile.x, y: tile.y });
  } else if (tile.mergedFrom) {
    // The merged tile stays hidden while its two sources slide in underneath.
    el.classList.add("tile-merged");
    for (const source of tile.mergedFrom) els.push(...createTileEls(source, movers));
  } else {
    el.classList.add("tile-new");
  }

  return els;
}

export function renderTiles(game: Game, layer: HTMLElement): void {
  const frag = document.createDocumentFragment();
  const movers: Mover[] = [];
  for (const tile of game.tiles()) {
    for (const el of createTileEls(tile, movers)) frag.appendChild(el);
  }
  layer.replaceChildren(frag);

  // Force a reflow so the "from" transforms become the transition's start
  // value, then write the targets — that's what makes the tiles slide.
  void layer.offsetHeight;
  for (const m of movers) position(m.el, m.x, m.y);
}

export function renderScore(
  els: Elements,
  game: Game,
  gained: number,
): void {
  els.score.textContent = String(game.score);
  els.best.textContent = String(game.best);
  if (gained > 0) {
    const pop = document.createElement("div");
    pop.className = "score-pop";
    pop.textContent = `+${gained}`;
    els.scoreBox.appendChild(pop);
    pop.addEventListener("animationend", () => pop.remove());
  }
}

export function renderOverlay(els: Elements, game: Game): void {
  const active = game.over || (game.won && !game.keepPlaying);
  els.overlay.classList.toggle("is-visible", active);
  els.overlay.classList.toggle("is-win", game.won && !game.over);
  if (!active) return;
  els.overlayTitle.textContent = game.won ? "Ти зробив 2048! 🎉" : "Гру закінчено";
}
