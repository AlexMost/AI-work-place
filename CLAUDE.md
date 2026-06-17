# AI-work-place

Umbrella-репозиторій з незалежними експериментами по AI/LangGraph. Кожна тека верхнього рівня — це окремий npm-проєкт зі своїми залежностями, своїм `package.json`, своєю збіркою. Це не моноріпо: між експериментами немає shared-коду.

## Поточні експерименти

- `fact-checker/` — TypeScript + LangGraph граф для фактчекінгу тексту. Має React/Vite UI (`src/ui`) і ядро (`src/core`). Тести на vitest, форматування prettier. Власний `.claude/` з додатковими дозволами і плагіном `frontend-design`.
- `langraph-quickstart/` — мінімальний LangGraph-агент на `tsx`, без UI і без тестів. Швидкі проби концептів.
- `code-agent/` — кодовий агент за мотивами статті [How to build an agent](https://ampcode.com/notes/how-to-build-an-agent). LangGraph + OpenAI, три tools (`read_file`/`list_files`/`edit_file`), REPL. Усе в одному `index.ts`.
- `2048/` — браузерна гра 2048 на TypeScript + Vite (без фреймворків). Неоновий glassmorphism-стиль, анімовані переходи плиток, керування клавіатурою і свайпом. Логіка в `src/game.ts`, рендер у `src/render.ts`. Деплой через `npm run publish-gh-pages`.

## Як працювати

- Завжди заходь у відповідну піддиректорію перед запуском команд (`cd fact-checker && npm run test`). Команди npm з кореня не спрацюють — `package.json` тут немає.
- Експерименти мають залишатися автономними. Не виноси код між ними і не створюй спільних пакетів без явного запиту користувача.
- Новий експеримент = нова директорія верхнього рівня зі своїм `package.json` + (за потреби) `langgraph.json`.
- `.env` лежить у піддиректоріях окремо для кожного експерименту; не комітити.

## Деплой на GitHub Pages

Live-сайт віддається з гілки **`gh-pages`** (Settings → Pages → Branch: `gh-pages` / root), **не з `main`** — тому `git push` у `main` оновлює лише джерело, а не live. Щоб оновити сайт, треба окремо задеплоїти.

- Підпроєкт зі скриптом `publish-gh-pages` публікується так: `cd <проєкт> && npm run publish-gh-pages`. Скрипт білдить статику і пушить її в підкаталог `<проєкт>/` гілки `gh-pages`.
- Під капотом — `gh-pages -e <subdir> --add`, тож деплой одного експерименту не зачіпає інші підкаталоги на `gh-pages`.
- URL: `https://alexmost.github.io/AI-work-place/<проєкт>/` (напр. `…/footbal/`).
- Для `footbal/` спершу регенеруй дашборд (`generate_dashboard.py`), і лише потім `npm run publish-gh-pages` — інакше на сайт поїде стара версія.

## Стек, який тут типово зустрічається

- Node 20+ / TypeScript
- `@langchain/langgraph`, `@langchain/openai`, `@langchain/core`, `zod`
- vitest для тестів, prettier для формату
- vite + React 19 там, де потрібен UI
- LangGraph CLI (`langgraph.json` у проєкті)

## Конвенції

- Коментарі писати тільки якщо WHY неочевидний — назв і типів зазвичай достатньо.
- Не додавати фічі/абстракції поза скоупом запиту.
- Перед тим як заявити, що задача зроблена, прогнати тести/тайпчек у відповідному піддиректорії, якщо вони там є.
