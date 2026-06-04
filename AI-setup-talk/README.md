# AI-setup-talk

HTML-презентація для доповіді **«AI basic setup — Harness-інженерія для агентів»**.
Movement: один `slides.md` → reveal.js → статичний HTML на GitHub Pages.

## Структура

| Файл | Роль |
| --- | --- |
| `slides.md` | **Єдине джерело контенту.** Тут пишеш слайди. |
| `src/theme.css` | Кастомна тема (палітра, шрифти, картки, сітки). |
| `index.html` | Каркас reveal.js + підключення шрифтів. |
| `src/main.js` | Ініціалізація reveal.js і плагінів. |

## Команди

```bash
npm install
npm run dev              # дев-сервер з hot-reload (редагуй slides.md — оновлюється миттєво)
npm run build            # збірка в dist/
npm run publish-gh-pages # збірка з base=/AI-work-place/AI-setup-talk/ + деплой на gh-pages
```

Опублікований URL: `https://<user>.github.io/AI-work-place/AI-setup-talk/`

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
бо на gh-pages сайт живе під `/AI-work-place/AI-setup-talk/`, і лише відносний шлях ураховує цей base.

```md
![Підпис](img/diagram.svg)
```

- Файл: `public/img/diagram.svg` → на сайті `img/diagram.svg` (приклад: `public/img/sample.svg`).
- Розтягнути на весь доступний простір слайда: `<img class="r-stretch" src="img/big.png" />`
- Фонове зображення слайда: `<!-- .slide: data-background-image="img/bg.jpg" -->`
- Розмір/позиція вручну — звичайний HTML: `<img src="img/logo.png" style="width: 320px" />`
- Зовнішні URL (`https://…`) теж працюють, але **для живої доповіді ризиковано** — без інтернету не завантажиться. Краще локально.

### Діаграми (Excalidraw)

Скіл `excalidraw-diagram` (у `.claude/skills/`) генерує `.excalidraw` JSON у темі деку
(палітра вже адаптована в `references/color-palette.md`: темний фон, бурштин/блакитний/фіолет).

Workflow:
1. Джерело діаграм — у `diagrams/*.excalidraw` (не в `public/`, щоб не роздавати JSON).
2. Експорт у **векторний SVG** (прозорий фон — щоб лягав на будь-який слайд):
   ```bash
   cd .claude/skills/excalidraw-diagram/references
   uv run python export_svg.py ../../../diagrams/harness-loop.excalidraw \
     --output ../../../public/img/harness-loop.svg
   ```
   (`--solid` лишає фон `#0a0e14` замість прозорого.)
3. Вставити у слайд як звичайне зображення: `<img src="img/harness-loop.svg" .../>`.

Для візуальної перевірки діаграми (PNG, не для деку): `uv run python render_excalidraw.py <file> --output /tmp/x.png`.

> Перший сетап рендерера (одноразово): `cd .claude/skills/excalidraw-diagram/references && uv sync && uv run playwright install chromium`.
> Приклад готової діаграми — `diagrams/harness-loop.excalidraw` → `public/img/harness-loop.svg` (слайд у секції Takeaway).

### Допоміжні класи теми

- `<span class="kicker">01</span>` — маленький моноширинний над-заголовок
- `<p class="muted">…</p>` — приглушений текст
- `<div class="cols"><div class="card">…</div><div class="card">…</div></div>` — дві колонки/картки

## Навігація під час показу

`←/→` гортати · `F` повний екран · `S` нотатки спікера · `O` огляд слайдів · `B` чорний екран
