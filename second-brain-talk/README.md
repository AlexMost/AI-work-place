# second-brain-talk

HTML-презентація для доповіді **«LLM Wiki vs Second Brain»** (дев-клуб, наступна після «Дві осі SDD»).
Movement: один `slides.md` → reveal.js → статичний HTML на GitHub Pages.

> Скелет доповіді (теза, хук, панчлайн) живе у vault: `Tasks/Скелет доповіді LLM Wiki vs Second Brain`.
> Сире зерно ідеї: `Inbox/Ідея доповіді — neuro-vault + Obsidian`.

## Структура

| Файл | Роль |
| --- | --- |
| `slides.md` | **Єдине джерело контенту.** Тут пишеш слайди. |
| `src/theme.css` | Кастомна тема (палітра, шрифти, картки, сітки). |
| `src/sketch.js` | Рукописне оформлення (рамки/стрілки/підкреслення, Excalidraw look). |
| `index.html` | Каркас reveal.js + favicon. |
| `src/main.js` | Ініціалізація reveal.js і плагінів. |

## Команди

```bash
npm install
npm run dev              # дев-сервер з hot-reload (редагуй slides.md — оновлюється миттєво)
npm run build            # збірка в dist/
npm run publish-gh-pages # збірка з base=/AI-work-place/second-brain-talk/ + деплой на gh-pages
```

Опублікований URL: `https://alexmost.github.io/AI-work-place/second-brain-talk/`

## Як писати слайди (`slides.md`)

- `---` на окремому рядку → **новий горизонтальний слайд**
- `--` на окремому рядку → **вертикальний слайд** (під поточним)
- Рядок `Note:` і все після нього в межах слайда → **нотатки спікера** (клавіша `S`)
- Конфіг конкретного слайда — HTML-коментарем:
  `<!-- .slide: data-background-color="#0d1320" -->`
- Анімація появи елемента (fragment):
  `текст <!-- .element: class="fragment" -->`

### Зображення

Картинки кладемо в `public/` — Vite роздає їх з кореня й копіює в `dist/` при збірці.
**Важливо:** шлях у markdown має бути **відносним без слеша на початку** (`img/foo.png`, а не `/img/foo.png`),
бо на gh-pages сайт живе під `/AI-work-place/second-brain-talk/`, і лише відносний шлях ураховує цей base.

```md
![Підпис](img/diagram.svg)
```

- Файл: `public/img/diagram.svg` → на сайті `img/diagram.svg`
- Розтягнути на весь доступний простір слайда: `<img class="r-stretch" src="img/big.png" />`
- Фонове зображення слайда: `<!-- .slide: data-background-image="img/bg.jpg" -->`
- Зовнішні URL (`https://…`) теж працюють, але **для живої доповіді ризиковано** — без інтернету не завантажиться. Краще локально.

### Рукописне оформлення (`data-sketch`)

`src/sketch.js` домальовує rough.js-декорації поверх звичайного HTML:

- Типи: `data-sketch="box | box-fill | ellipse | circle-note | underline | highlight | strike"`
- Кольори: `data-stroke="ink|red|blue|green|orange|violet|gray"`, `data-fill="red|blue|green|yellow|violet|gray"`
- Стрілки між елементами (всередині контейнера з `data-sketch-scope`):
  `<div data-arrow-from="#a" data-arrow-to="#b" data-stroke="blue"></div>`

### Допоміжні класи теми

- `<span class="kicker">01</span>` — маленький моноширинний над-заголовок
- `<p class="muted">…</p>` — приглушений текст
- `<div class="cols"><div class="card">…</div><div class="card">…</div></div>` — дві колонки/картки

## Навігація під час показу

`←/→` гортати · `F` повний екран · `S` нотатки спікера · `O` огляд слайдів · `B` чорний екран
