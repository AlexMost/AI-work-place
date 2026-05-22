# fact-checker

LangGraph-агент, який перевіряє фактологічність українського тексту через Wikipedia. Має React/Vite UI поверх ядра.

## Архітектура

Пайплайн `checkText` (`src/core/checkText.ts`):
1. `extractClaimsFromText` — LLM витягує атомарні твердження з тексту (`src/core/claimExtraction.ts`).
2. `locateExtractedClaims` — мапить кожне твердження назад на span `[start, end]` у вихідному тексті (`src/core/claimLocation.ts`). Твердження, які не вдалося прив'язати, ідуть у `notEnoughInfo` без виклику LLM.
3. `checkFact` — для кожного знайденого твердження запускається граф (`src/core/factCheck.ts` + `src/core/graph.ts`), який ходить у Wikipedia tools і повертає `SUPPORTED | REFUTED | NOT_ENOUGH_INFO` з поясненням. Перевірки виконуються паралельно через `Promise.all`.

Граф вибирає мовну версію Wikipedia за темою (українська vs англійська) — це у системному промпті в `graph.ts`. Tools у `src/core/tools.ts`.

`src/core/debugGraph.ts` — окремий entry для LangGraph CLI (див. `langgraph.json`), `src/core/debug.ts` — `debugLog` helper.

UI (`src/ui/`) — React 19 + Vite, незалежний `tsconfig.ui.json`. Підключається до ядра напряму через імпорти з `src/core`.

## Команди

Усе запускати з `fact-checker/`:

- `npm run dev` — CLI demo (`src/core/index.ts`, потрібен `OPENAI_API_KEY` в `.env`).
- `npm run dev:ui` / `npm run build:ui` — Vite dev/build.
- `npm run build` — `tsc` для ядра.
- `npm test` / `npm run test:watch` — vitest.
- `npm run format` / `npm run format:check` — prettier по `src/**` і `tests/**`.
- `npm run dev:graph` — LangGraph Studio проти `langgraph.json` (граф `fact_checker` = `debugGraph`).

## Конвенції

- Промпти та user-facing тексти — українською; код, типи, log-теги — англійською (див. `debugLog('claim:check:start', ...)`).
- Не міксувати UI- і core-залежності: усе, що в `src/core`, має лишатися імпортованим з Node без React. UI імпортує core, не навпаки.
- Помилки одного claim не валять весь пайплайн — обгортка в `checkText` ловить їх і кидає твердження у `notEnoughInfo`. Дотримуватися цього при додаванні нових кроків.
- Тести на vitest у `tests/`, файли `*.test.ts`. Юніт-тести не повинні ходити в мережу або OpenAI — мокати tools/LLM.
- Перед PR: `npm run format:check && npx tsc --noEmit && npm test`.

## Зовнішні залежності

- OpenAI API (`OPENAI_API_KEY` у `fact-checker/.env`).
- Wikipedia REST API — без ключа; rate-limit модерований, але не зловживати в тестах.

## Що НЕ робити

- Не виносити логіку в корінь репозиторію — це автономний експеримент.
- Не додавати моки на рівні `checkText` "щоб обійти OpenAI" — мокати точку входу в LLM/tools, а не сам пайплайн.
- Не оновлювати моделі/SDK з мажорними версіями `@langchain/*` без перевірки графа в Studio.
