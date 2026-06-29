/* =========================================================================
   sketch.js — first-party hand-drawn decoration engine (Excalidraw look).
   Recreation of the design system's sketch behavior, authored for this deck.
   Uses the bundled rough.js (npm) — no external/CDN code.

   Decorates plain HTML via [data-sketch]:
     box | box-fill | ellipse | circle-note | underline | highlight | strike
   Modifiers:
     data-stroke="ink|red|blue|green|orange|violet|gray"
     data-fill="red|blue|green|yellow|violet|gray"
     data-fill-style="hachure|solid|cross-hatch|zigzag"
     data-rough="1.2"  data-sw="2.4"  data-r="10"
   Scoped arrows (inside a [data-sketch-scope] container):
     <div data-arrow-from="#a" data-arrow-to="#b" data-stroke="blue" data-dash="true"></div>
   ========================================================================= */
import rough from 'roughjs';

const COLORS = {
  ink: '#1e1e1e', red: '#e03131', blue: '#1971c2', green: '#2f9e44',
  orange: '#f08c00', violet: '#9c36b5', gray: '#868e96',
};
const FILLS = {
  red: '#ffc9c9', blue: '#a5d8ff', green: '#b2f2bb',
  yellow: '#ffec99', violet: '#eebefa', gray: '#e9ecef',
};
const NS = 'http://www.w3.org/2000/svg';

let _uid = 0;
function seedOf(str) {
  let h = 2166136261;
  for (let i = 0; i < str.length; i++) { h ^= str.charCodeAt(i); h = Math.imul(h, 16777619); }
  return Math.abs(h) % 100000;
}
function keyOf(el) {
  if (!el.__skKey) el.__skKey = (el.id || 'sk') + '-' + _uid++;
  return el.__skKey;
}
function mkSvg() {
  const s = document.createElementNS(NS, 'svg');
  s.setAttribute('class', 'sketch-overlay');
  Object.assign(s.style, { position: 'absolute', left: '0', top: '0', overflow: 'visible', pointerEvents: 'none', zIndex: '0' });
  return s;
}
function baseOpts(el) {
  return {
    stroke: COLORS[el.dataset.stroke] || COLORS.ink,
    strokeWidth: parseFloat(el.dataset.sw) || 2.4,
    roughness: el.dataset.rough != null ? parseFloat(el.dataset.rough) : 1.2,
    bowing: 1.1,
    seed: seedOf(keyOf(el)),
  };
}
function roundRectPath(x, y, w, h, r) {
  r = Math.min(r, w / 2, h / 2);
  return `M${x + r},${y} h${w - 2 * r} a${r},${r} 0 0 1 ${r},${r} v${h - 2 * r} a${r},${r} 0 0 1 ${-r},${r} h${-(w - 2 * r)} a${r},${r} 0 0 1 ${-r},${-r} v${-(h - 2 * r)} a${r},${r} 0 0 1 ${r},${-r} z`;
}

function decorateOne(el) {
  const kind = el.dataset.sketch;
  if (!kind) return;
  if (el.__skSvg && el.__skSvg.parentNode) el.__skSvg.parentNode.removeChild(el.__skSvg);
  if (getComputedStyle(el).position === 'static') el.style.position = 'relative';

  const w = el.offsetWidth, h = el.offsetHeight;
  if (!w || !h) return;

  const svg = mkSvg();
  svg.setAttribute('width', w);
  svg.setAttribute('height', h);
  svg.setAttribute('viewBox', `0 0 ${w} ${h}`);
  const rc = rough.svg(svg);
  const o = baseOpts(el);
  const pad = (o.strokeWidth || 2) + 2;
  let node;

  if (kind === 'box' || kind === 'box-fill') {
    const r = el.dataset.r != null ? parseFloat(el.dataset.r) : 10;
    const x = pad, y = pad, bw = w - pad * 2, bh = h - pad * 2;
    if (kind === 'box-fill') {
      o.fill = FILLS[el.dataset.fill] || FILLS.yellow;
      o.fillStyle = el.dataset.fillStyle || 'hachure';
      o.fillWeight = parseFloat(el.dataset.fillWeight) || 2;
      o.hachureGap = parseFloat(el.dataset.hachureGap) || 7;
      o.hachureAngle = parseFloat(el.dataset.hachureAngle) || -41;
    }
    node = r > 0 ? rc.path(roundRectPath(x, y, bw, bh, r), o) : rc.rectangle(x, y, bw, bh, o);
  } else if (kind === 'ellipse') {
    if (el.dataset.fill) { o.fill = FILLS[el.dataset.fill]; o.fillStyle = el.dataset.fillStyle || 'hachure'; o.hachureGap = 7; }
    node = rc.ellipse(w / 2, h / 2, w - pad * 2, h - pad * 2, o);
  } else if (kind === 'circle-note') {
    o.fill = 'none';
    node = rc.ellipse(w / 2, h / 2, w + 14, h + 10, o);
    svg.style.overflow = 'visible';
  } else if (kind === 'underline') {
    const yy = h - pad;
    node = rc.linearPath([[pad, yy], [w * 0.33, yy - 2], [w * 0.66, yy + 2], [w - pad, yy - 1]], o);
  } else if (kind === 'strike') {
    node = rc.line(pad, h / 2, w - pad, h / 2, o);
  } else if (kind === 'highlight') {
    o.fill = FILLS[el.dataset.fill] || FILLS.yellow;
    o.fillStyle = el.dataset.fillStyle || 'solid';
    o.stroke = 'none';
    o.roughness = 1.6;
    node = rc.rectangle(pad, h * 0.18, w - pad * 2, h * 0.74, o);
  }

  if (!node) return;
  svg.appendChild(node);
  el.insertBefore(svg, el.firstChild);
  el.__skSvg = svg;
  if (kind === 'highlight') { svg.style.zIndex = '0'; el.style.zIndex = '1'; }
  // lift real content above the overlay
  Array.prototype.forEach.call(el.children, (c) => {
    if (c !== svg && getComputedStyle(c).position === 'static') { c.style.position = 'relative'; c.style.zIndex = '1'; }
  });
}

/* ---- scoped connectors (arrows) ---- */
function offsetWithin(el, scope) {
  let x = 0, y = 0, node = el;
  while (node && node !== scope && node !== document.body) { x += node.offsetLeft; y += node.offsetTop; node = node.offsetParent; }
  return { left: x, top: y, width: el.offsetWidth, height: el.offsetHeight, right: x + el.offsetWidth, bottom: y + el.offsetHeight };
}
function anchor(rect, side) {
  switch (side) {
    case 'top': return [rect.left + rect.width / 2, rect.top];
    case 'bottom': return [rect.left + rect.width / 2, rect.bottom];
    case 'left': return [rect.left, rect.top + rect.height / 2];
    case 'right': return [rect.right, rect.top + rect.height / 2];
    default: return [rect.left + rect.width / 2, rect.top + rect.height / 2];
  }
}
function nearestSides(a, b) {
  const dx = (b.left + b.width / 2) - (a.left + a.width / 2);
  const dy = (b.top + b.height / 2) - (a.top + a.height / 2);
  if (Math.abs(dx) > Math.abs(dy)) return dx > 0 ? ['right', 'left'] : ['left', 'right'];
  return dy > 0 ? ['bottom', 'top'] : ['top', 'bottom'];
}
function drawConnector(rc, layer, d, p1, p2) {
  const stroke = COLORS[d.dataset.stroke] || COLORS.ink;
  const sw = parseFloat(d.dataset.sw) || 2.6;
  const seed = seedOf((d.dataset.arrowFrom || '') + (d.dataset.arrowTo || ''));
  const opt = { stroke, strokeWidth: sw, roughness: d.dataset.rough != null ? parseFloat(d.dataset.rough) : 1.05, bowing: 1.3, seed };
  if (d.dataset.dash === 'true') opt.strokeLineDash = [8, 7];
  const curve = parseFloat(d.dataset.curve) || 0;
  const mx = (p1[0] + p2[0]) / 2 + (p2[1] - p1[1]) * curve;
  const my = (p1[1] + p2[1]) / 2 - (p2[0] - p1[0]) * curve;
  layer.appendChild(rc.curve([p1, [mx, my], p2], opt));
  if (d.dataset.head !== 'none') {
    const ang = Math.atan2(p2[1] - my, p2[0] - mx);
    const L = parseFloat(d.dataset.headSize) || 15;
    const aOpt = { stroke, strokeWidth: sw, roughness: 0.9, seed: seed + 1 };
    layer.appendChild(rc.line(p2[0], p2[1], p2[0] - L * Math.cos(ang - 0.42), p2[1] - L * Math.sin(ang - 0.42), aOpt));
    layer.appendChild(rc.line(p2[0], p2[1], p2[0] - L * Math.cos(ang + 0.42), p2[1] - L * Math.sin(ang + 0.42), aOpt));
  }
}
function drawArrows() {
  document.querySelectorAll('[data-sketch-scope]').forEach((scope) => {
    const defs = scope.querySelectorAll('[data-arrow-from]');
    if (!defs.length) return;
    if (getComputedStyle(scope).position === 'static') scope.style.position = 'relative';
    let svg = scope.__arrowSvg;
    if (!svg || svg.parentNode !== scope) { svg = mkSvg(); scope.insertBefore(svg, scope.firstChild); scope.__arrowSvg = svg; }
    const w = scope.offsetWidth, h = scope.offsetHeight;
    if (!w || !h) return;
    svg.setAttribute('width', w); svg.setAttribute('height', h); svg.setAttribute('viewBox', `0 0 ${w} ${h}`);
    svg.innerHTML = '';
    const rc = rough.svg(svg);
    defs.forEach((d) => {
      const a = scope.querySelector(d.dataset.arrowFrom);
      const b = scope.querySelector(d.dataset.arrowTo);
      if (!a || !b) return;
      const ra = offsetWithin(a, scope), rb = offsetWithin(b, scope);
      const sides = nearestSides(ra, rb);
      drawConnector(rc, svg, d, anchor(ra, d.dataset.fromSide || sides[0]), anchor(rb, d.dataset.toSide || sides[1]));
    });
  });
}

let raf = null;
export function refreshSketch() {
  if (raf) cancelAnimationFrame(raf);
  raf = requestAnimationFrame(() => {
    document.querySelectorAll('[data-sketch]').forEach(decorateOne);
    drawArrows();
  });
}
export function initSketch() {
  refreshSketch();
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(refreshSketch);
  window.addEventListener('resize', refreshSketch);
}
