# Від вайбкодінгу до AI-інженерії — слайди (evo AI DAY)

reveal.js-презентація за скелетом `AI-setup-talk`: весь контент живе в одному
[slides.md](slides.md), оформлення — фірмовий стиль evo AI DAY (фони витягнуті
з офіційного Google Slides шаблону івенту).

План доповіді й таймінги: [plan.md](plan.md).

## Як працювати

```bash
npm install
npm run dev        # локальний перегляд з hot reload
npm run build      # збірка в dist/
npm run publish-gh-pages
```

- `---` — новий горизонтальний слайд, `--` — вертикальний, `Note:` — нотатки спікера
  (відкриваються клавішею `S` у режимі доповідача).
- Фони: `public/img/bg/` (title / frame / swirl / flower). Дефолтний фон (frame) заданий
  на viewport у `src/theme.css`; окремі слайди перекривають його через
  `<!-- .slide: data-background-image="img/bg/….jpg" -->`.
- Скляні 3D-елементи шаблону: `public/img/el/` — вставляються як `<img class="deco plain" …>`.
- Шрифт Montserrat бандлиться локально через `@fontsource/montserrat` — інтернет на
  майданчику не потрібен.

## TODO перед виступом

- скріншоти OpenSpec-флоу (propose → apply) у слайд «OpenSpec: живий приклад»
- фінальне формулювання відкритого питання на слайді «Питання до вас»
- прогнати таймінг (~36–38 хв)
