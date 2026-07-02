# Баг openspec: `schema init --default` пише `defaultSchema`, а reader читає `schema` (мовчазний no-op)

Учень у `openspec-demo/openspec/config.yaml` мав `schema: spec-driven` + `defaultSchema: my-shcema` і не розумів другий ключ. Розкрито до кінця (сирці + live-експеримент):

**Походження**: рядок згенерував сам openspec — крок `openspec schema init my-shcema` → «Set as project default schema? Yes». Код: `src/commands/schema.ts:877` (`config.defaultSchema = name`) і `:885`. (Спершу я помилково сказав, що openspec цього не пише — бо перевірив `serializeConfig` зі шляху `openspec init`, а не шлях `schema init`. Виправлено.)

**Баг**: writer кладе ключ `defaultSchema`, а весь reader-код (`ProjectConfigSchema` project-config.ts:19-54; `resolveSchemaForChange`) читає лише `schema`. Розходження назв → «Set as default» НЕ застосовується. Емпірично: нова зміна з `defaultSchema: lab-schema` у конфігу все одно отримала `spec-driven`. CLI друкує «Set as project default schema.», але дефолт не змінюється.

**Друга шкода того ж коду**: `parseYaml → stringifyYaml` round-trip стирає всі коментарі з config.yaml.

**Фікс**: руками `schema: my-shcema`, видалити `defaultSchema`. `openspec config set` тут не годиться — то інший (глобальний) конфіг.

**Evidence**: учень надав повний лог `schema init` з «Set as project default schema? Yes»; я знайшов writer (schema.ts:877,885) і reader (project-config.ts) + відтворив no-op у scratchpad-lab.

**Implications**:
- Загальний трансфер лишається: config.yaml **мовчки ігнорує незнайомі ключі верхнього рівня** (resilient-парсер) — на відміну від битого artifactId усередині `rules`, який ДАЄ warning. Тобто помилка в назві ключа = тихий no-op; при дебагу звіряти ключі зі списком дозволених.
- `schema`-команди openspec ЕКСПЕРИМЕНТАЛЬНІ (CLI сам попереджає) — не покладатись на них у демо доповіді без перевірки. Цей баг — кандидат на GitHub issue (перегук з RESOURCES: спільнота/wisdom).
- Модель «`schema:` у config = єдиний дефолт для НОВИХ змін; існуючі запінені в `.openspec.yaml`» підтверджена ще раз.
