export type Direction = "up" | "down" | "left" | "right";

export interface Position {
  x: number; // column, 0 = left
  y: number; // row, 0 = top
}

export interface Tile extends Position {
  id: number;
  value: number;
  prev: Position | null; // where it was before the last move (for slide animation)
  mergedFrom: [Tile, Tile] | null; // the two tiles that combined into this one
}

export interface MoveResult {
  moved: boolean;
  gained: number; // points scored this move
}

const VECTORS: Record<Direction, Position> = {
  up: { x: 0, y: -1 },
  down: { x: 0, y: 1 },
  left: { x: -1, y: 0 },
  right: { x: 1, y: 0 },
};

export class Game {
  readonly size: number;
  cells: (Tile | null)[][]; // cells[x][y]
  score = 0;
  best = 0;
  over = false;
  won = false;
  keepPlaying = false;

  private nextId = 1;

  constructor(size = 4) {
    this.size = size;
    this.cells = this.emptyGrid();
  }

  private emptyGrid(): (Tile | null)[][] {
    return Array.from({ length: this.size }, () =>
      Array.from({ length: this.size }, () => null),
    );
  }

  setup(best = 0): void {
    this.cells = this.emptyGrid();
    this.score = 0;
    this.best = best;
    this.over = false;
    this.won = false;
    this.keepPlaying = false;
    this.nextId = 1;
    this.addRandomTile();
    this.addRandomTile();
  }

  /** All tiles currently on the board, top-left reading order. */
  tiles(): Tile[] {
    const out: Tile[] = [];
    for (let y = 0; y < this.size; y++) {
      for (let x = 0; x < this.size; x++) {
        const t = this.cells[x][y];
        if (t) out.push(t);
      }
    }
    return out;
  }

  private availableCells(): Position[] {
    const out: Position[] = [];
    for (let x = 0; x < this.size; x++) {
      for (let y = 0; y < this.size; y++) {
        if (!this.cells[x][y]) out.push({ x, y });
      }
    }
    return out;
  }

  addRandomTile(): void {
    const cells = this.availableCells();
    if (cells.length === 0) return;
    const pos = cells[Math.floor(Math.random() * cells.length)];
    const value = Math.random() < 0.9 ? 2 : 4;
    this.cells[pos.x][pos.y] = {
      id: this.nextId++,
      value,
      x: pos.x,
      y: pos.y,
      prev: null,
      mergedFrom: null,
    };
  }

  private withinBounds(p: Position): boolean {
    return p.x >= 0 && p.x < this.size && p.y >= 0 && p.y < this.size;
  }

  /** Walk from `cell` along `vector` to the farthest free cell; report the cell beyond it. */
  private farthestPosition(
    cell: Position,
    vector: Position,
  ): { farthest: Position; next: Position } {
    let previous: Position;
    let current = cell;
    do {
      previous = current;
      current = { x: previous.x + vector.x, y: previous.y + vector.y };
    } while (this.withinBounds(current) && !this.cells[current.x][current.y]);
    return { farthest: previous, next: current };
  }

  private buildTraversals(vector: Position): { xs: number[]; ys: number[] } {
    const xs: number[] = [];
    const ys: number[] = [];
    for (let i = 0; i < this.size; i++) {
      xs.push(i);
      ys.push(i);
    }
    // Always traverse from the far end relative to movement direction.
    if (vector.x === 1) xs.reverse();
    if (vector.y === 1) ys.reverse();
    return { xs, ys };
  }

  move(direction: Direction): MoveResult {
    if (this.over || (this.won && !this.keepPlaying)) {
      return { moved: false, gained: 0 };
    }

    const vector = VECTORS[direction];
    const { xs, ys } = this.buildTraversals(vector);
    let moved = false;
    let gained = 0;

    // Reset per-move animation bookkeeping.
    for (const tile of this.tiles()) {
      tile.prev = { x: tile.x, y: tile.y };
      tile.mergedFrom = null;
    }

    for (const x of xs) {
      for (const y of ys) {
        const tile = this.cells[x][y];
        if (!tile) continue;

        const { farthest, next } = this.farthestPosition({ x, y }, vector);
        const target = this.withinBounds(next) ? this.cells[next.x][next.y] : null;

        if (target && target.value === tile.value && !target.mergedFrom) {
          // Merge tile into target.
          const merged: Tile = {
            id: this.nextId++,
            value: tile.value * 2,
            x: next.x,
            y: next.y,
            prev: null,
            mergedFrom: [tile, target],
          };
          this.cells[next.x][next.y] = merged;
          this.cells[x][y] = null;
          tile.x = next.x;
          tile.y = next.y; // so the consumed tile slides into place before vanishing

          gained += merged.value;
          if (merged.value === 2048) this.won = true;
          moved = true;
        } else {
          this.moveTile(tile, farthest);
          if (farthest.x !== x || farthest.y !== y) moved = true;
        }
      }
    }

    if (moved) {
      this.score += gained;
      if (this.score > this.best) this.best = this.score;
      this.addRandomTile();
      if (!this.movesAvailable()) this.over = true;
    }

    return { moved, gained };
  }

  private moveTile(tile: Tile, to: Position): void {
    this.cells[tile.x][tile.y] = null;
    this.cells[to.x][to.y] = tile;
    tile.x = to.x;
    tile.y = to.y;
  }

  private movesAvailable(): boolean {
    if (this.availableCells().length > 0) return true;
    for (let x = 0; x < this.size; x++) {
      for (let y = 0; y < this.size; y++) {
        const tile = this.cells[x][y];
        if (!tile) continue;
        for (const dir of Object.values(VECTORS)) {
          const other = { x: x + dir.x, y: y + dir.y };
          if (this.withinBounds(other)) {
            const neighbor = this.cells[other.x][other.y];
            if (neighbor && neighbor.value === tile.value) return true;
          }
        }
      }
    }
    return false;
  }
}
