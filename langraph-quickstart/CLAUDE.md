# langraph-quickstart

Мінімальний LangGraph-агент для проби концептів: арифметика через tools + human-in-the-loop через `interrupt`. Не виробничий код, не несе нічого зовні — це піщана коробка.

## Архітектура

Один файл `index.ts` — граф із двох вузлів:

- `llmCall` — кличе `modelWithTools` із системним промптом про арифметику. Якщо запит неоднозначний, модель має викликати `ask_clarification`.
- `toolNode` — виконує усі `tool_calls` з останнього `AIMessage` і повертає `ToolMessage[]`.
- `shouldContinue` — conditional edge: якщо є `tool_calls` → `toolNode`, інакше `END`.

Граф компілюється з `MemorySaver` і експортується як `agent`. LangGraph CLI підхоплює його через `langgraph.json` (`graphs.agent = ./index.ts:agent`).

Tools у `tools.ts`: `add`, `multiply`, `divide`, `ask_clarification` (останній — це `interrupt(question)`, тобто пауза графа з очікуванням `Command({ resume: ... })`). Модель у `model.ts`, state-схема в `state.ts`.

## Команди

Усе з `langraph-quickstart/`:

- `npm start` — запускає `tsx index.ts` (зараз invoke закоментований у файлі; розкоментувати або викликати з REPL/Studio).
- `npx @langchain/langgraph-cli dev` — LangGraph Studio, граф `agent`. Через Studio зручно тестувати `interrupt`/`resume`.

Потрібен `OPENAI_API_KEY` у `langraph-quickstart/.env` (шлях прописаний у `langgraph.json`).

## Конвенції

- Це quickstart, тому фокус — мінімалізм. Не додавати фреймворків, layered-архітектури, тестів, форматування — це шумить у "пісочниці".
- ESM проєкт (`"type": "module"`) на відміну від `fact-checker` (CommonJS). Не копіювати імпорти/конфіги між цими двома проєктами наосліп.
- Якщо концепт виростає у щось більше — виносити в окрему директорію верхнього рівня, а не розширювати цей.

## Що НЕ робити

- Не додавати prettier/eslint/vitest сюди — для цього є `fact-checker`.
- Не намагатися мерджити цей агент з `fact-checker` — різні цілі, різні модулі.
