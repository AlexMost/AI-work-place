# AI-work-place

Збірка незалежних AI/LangGraph експериментів. Кожна тека верхнього рівня — це окремий npm-проєкт зі своїм `package.json`.

## Експерименти

| Проєкт | Опис | Демо |
| --- | --- | --- |
| [`fact-checker/`](./fact-checker) | LangGraph-агент фактчекінгу українського тексту через Wikipedia, з React/Vite UI | [демо](https://alexmost.github.io/AI-work-place/fact-checker/) |
| [`AI-setup-talk/`](./AI-setup-talk) | reveal.js-презентація «AI basic setup — Harness-інженерія для агентів» з одного `slides.md` | [демо](https://alexmost.github.io/AI-work-place/AI-setup-talk/) |
| [`openspec-talk/`](./openspec-talk) | reveal.js-презентація «Дві осі SDD — специфікація і процес» з одного `slides.md` | [демо](https://alexmost.github.io/AI-work-place/openspec-talk/) |
| [`quick-sort-teach-skill/`](./quick-sort-teach-skill) | Інтерактивні HTML-уроки (quicksort, TS generics) із швидким зворотним зв'язком | [демо](https://alexmost.github.io/AI-work-place/quick-sort-teach-skill/) |
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
