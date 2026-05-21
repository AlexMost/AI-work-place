# AI-work-place

Збірка незалежних AI/LangGraph експериментів. Кожна тека верхнього рівня — це окремий npm-проєкт зі своїм `package.json`.

## Експерименти

| Проєкт | Опис | Демо |
| --- | --- | --- |
| [`fact-checker/`](./fact-checker) | LangGraph-агент фактчекінгу українського тексту через Wikipedia, з React/Vite UI | [демо](https://alexmost.github.io/AI-work-place/fact-checker/) |
| [`code-agent/`](./code-agent) | Мінімальний кодовий агент (LangGraph + OpenAI) з трьома tools і REPL | — |
| [`langraph-quickstart/`](./langraph-quickstart) | Мінімальний LangGraph-агент на `tsx`, проби концептів | — |

## Публікація на GitHub Pages

Конвенція: якщо в підпроєкті є скрипт `publish-gh-pages`, його запуск білдить UI і пушить результат у subdirectory `gh-pages` branch (наприклад, `fact-checker/`).

```bash
cd fact-checker
npm run publish-gh-pages
```

Перший запуск створює `gh-pages` branch автоматично. Після цього треба один раз увімкнути GitHub Pages у налаштуваннях репозиторію: **Settings → Pages → Branch: `gh-pages` / root**.

Скрипт використовує `gh-pages -e <subdir> --add`, тому публікація одного експерименту не зачіпає інші підкаталоги на `gh-pages` branch.
