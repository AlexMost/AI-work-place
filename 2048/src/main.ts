import "./style.css";
import { Game, type Direction } from "./game";
import { bindInput } from "./input";
import {
  buildBackground,
  renderTiles,
  renderScore,
  renderOverlay,
  type Elements,
} from "./render";

const BEST_KEY = "2048.best";

function el<T extends HTMLElement>(id: string): T {
  const node = document.getElementById(id);
  if (!node) throw new Error(`Missing #${id}`);
  return node as T;
}

const els: Elements = {
  grid: el("grid"),
  tiles: el("tiles"),
  score: el("score"),
  best: el("best"),
  scoreBox: el("score-box"),
  overlay: el("overlay"),
  overlayTitle: el("overlay-title"),
  overlayActions: el("overlay-actions"),
};

const game = new Game(4);

function loadBest(): number {
  const raw = localStorage.getItem(BEST_KEY);
  const n = raw ? Number.parseInt(raw, 10) : 0;
  return Number.isFinite(n) ? n : 0;
}

function persistBest(): void {
  localStorage.setItem(BEST_KEY, String(game.best));
}

function draw(gained = 0): void {
  renderTiles(game, els.tiles);
  renderScore(els, game, gained);
  renderOverlay(els, game);
}

function newGame(): void {
  game.setup(loadBest());
  draw();
}

function handleMove(dir: Direction): void {
  const { moved, gained } = game.move(dir);
  if (!moved) return;
  persistBest();
  draw(gained);
}

buildBackground(els.grid, game.size);
bindInput(el("board"), handleMove);

el("new-game").addEventListener("click", newGame);
el("overlay-restart").addEventListener("click", newGame);
el("keep-playing").addEventListener("click", () => {
  game.keepPlaying = true;
  renderOverlay(els, game);
});

newGame();
