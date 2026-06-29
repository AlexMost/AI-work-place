import Reveal from 'reveal.js';
import Markdown from 'reveal.js/plugin/markdown';
import Highlight from 'reveal.js/plugin/highlight';
import Notes from 'reveal.js/plugin/notes';

import 'reveal.js/reveal.css';
import 'reveal.js/plugin/highlight/monokai.css';
import './theme.css';

// Намальоване від руки оформлення (рамки/стрілки/підкреслення) — Excalidraw look.
import { initSketch, refreshSketch } from './sketch.js';

// Єдине джерело правди для слайдів. ?raw → вбудовується в бандл як рядок,
// тож деплой на gh-pages не залежить від fetch/CORS/base-шляху.
import slides from '../slides.md?raw';

// Markdown-плагін парсить вміст <textarea> при initialize(), тож вставляємо до нього.
document.getElementById('slides-md').textContent = slides;

const deck = new Reveal({
  plugins: [Markdown, Highlight, Notes],
  hash: true,
  slideNumber: 'c/t',
  transition: 'slide',
  // speaker-led: трохи більший простір під контент
  width: 1280,
  height: 720,
  margin: 0.08,
});

deck.initialize().then(() => {
  initSketch();
  // перемальовувати рукописні рамки/стрілки, коли слайд став активним (видимим)
  deck.on('slidechanged', refreshSketch);
  deck.on('fragmentshown', refreshSketch);
  deck.on('fragmenthidden', refreshSketch);
});
