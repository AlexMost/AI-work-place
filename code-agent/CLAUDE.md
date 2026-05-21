# code-agent

Мінімалістичний кодовий агент за мотивами [How to build an agent](https://ampcode.com/notes/how-to-build-an-agent) (Thorsten Ball). Альтернативна реалізація: TypeScript + LangGraph + OpenAI замість Go + Anthropic. Усе в одному файлі `index.ts`.

## Архітектура

Двовузловий граф через `MessagesAnnotation`:

- `agent` — `ChatOpenAI` з прив'язаними tools, викликає LLM на повній історії.
- `tools` — стандартний `ToolNode` з `@langchain/langgraph/prebuilt`.
- Conditional edge: якщо в останньому `AIMessage` є `tool_calls` → `tools`, інакше → `END`. Після `tools` повертаємось у `agent`.

Tools (визначені прямо в `index.ts` через `tool()` + zod):

- `read_file({ path })` — `fs.readFile`.
- `list_files({ path? })` — `fs.readdir` з трейлінг-слешем для директорій, повертає JSON.
- `edit_file({ path, old_str, new_str })` — заміна першого входження `old_str` на `new_str`. Якщо файл не існує і `old_str === ''` — створює новий (з `mkdir -p` для батьківської директорії). Файл існує і `old_str === ''` — помилка (щоб не префіксувати випадково).

REPL у функції `repl()`: тримає `messages: BaseMessage[]` як локальну змінну, при кожному запиті дописує `HumanMessage` і ре-інвокає граф з усією історією. Без `MemorySaver` — простіше і явніше.

Експортується `agent`, тому LangGraph Studio підхоплює його з `langgraph.json` (граф `code_agent`).

## Команди

Усе з `code-agent/`:

- `npm start` — REPL (`tsx index.ts`). Потрібен `OPENAI_API_KEY` у `code-agent/.env`. Опціонально `OPENAI_MODEL` (за замовчуванням `gpt-5.4-mini`).
- `npm run studio` — LangGraph Studio проти графа `code_agent`.
- `npx tsc --noEmit` — тайпчек.

## Цілі і не-цілі

- Ціль: мінімальна повна реалізація патерну з статті. Зараз ~110 рядків в одному файлі.
- Це не виробничий код. Немає sandboxing — `edit_file` пише будь-куди, куди дозволяє ОС. Запускати тільки в директорії, де можна щось зламати.
- Не додавати: streaming, многотредовість, persistence, prompt engineering, нові tools "про всяк випадок". Якщо хочеться розширювати — або обережно інлайнити в той самий файл, або форкати в новий експеримент.

## Що відрізняється від оригіналу

- Anthropic → OpenAI: модель через `ChatOpenAI`, native function calling. Системний промпт відсутній — як і в статті, опис у `description` кожного tool.
- Go → TypeScript: ESM, `tsx` для запуску, `fs/promises`.
- Замість ручного циклу tool-calls — LangGraph граф з conditional edge. Це додає трохи церемонії, але виносить REPL з логіки агента і дає Studio "безкоштовно".
