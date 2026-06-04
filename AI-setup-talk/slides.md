<!-- .slide: data-background-color="#ffffff" -->

<span class="kicker">AI / Engineering</span>

# AI basic setup

<p class="muted">як ми зібрали AI-сетап у проєкті — <span data-sketch="circle-note" data-stroke="red" style="padding:2px 10px">з нуля</span></p>

<div style="display:flex;gap:16px;justify-content:center;flex-wrap:wrap;margin-top:18px">
<span class="chip" data-sketch="box-fill" data-stroke="ink" data-fill="yellow" data-r="9">skills</span>
<span class="chip" data-sketch="box" data-stroke="ink" data-r="9">rules</span>
<span class="chip" data-sketch="box" data-stroke="ink" data-r="9">plugins</span>
<span class="chip" data-sketch="box-fill" data-stroke="blue" data-fill="blue" data-r="9">MCP</span>
</div>

<p class="muted" style="margin-top:28px">Олександр Мостовенко</p>

---

# Harness

--

# AI Agent = LLM + Harness

--

<img src="img/what-is-harness.svg" alt="Harness — усе, що оточує модель: контекст, інструменти, межі, зворотний зв'язок" style="width: 84%; max-height: 74vh; border: none; background: none; box-shadow: none;" />

--

# Harness engineering for coding agent users

## https://martinfowler.com/articles/harness-engineering.html

![qr-harness](img/harness-qr.png)

--

# Harness engineering codex

## https://openai.com/uk-UA/index/harness-engineering/

![qr-codex](img/codex-qr.png)

--

<img src="img/harness-overview.png" alt="" style="max-height: 74vh; border: none; background: none; box-shadow: none;" />

--

# Sensors
## lints, type system, tests, CI, hooks

--

# Guides
## AGENTS.md, skills, rules, MCP, docs (adr, spec), architecture

--

<img src="img/sensors-guides-rails.svg" alt="LLM петляє, а sensors і guides ведуть її в напрямі цілі" style="width: 88%; max-height: 72vh; border: none; background: none; box-shadow: none;" />

---

<!-- .slide: data-background-color="#ffffff" -->

<span class="kicker">02</span>

# Guides

--

<img src="img/agent-context.svg" alt="Агент читає свій контекст: AGENTS.md, skills, rules, MCP" style="width: 90%; max-height: 72vh; border: none; background: none; box-shadow: none;" />

--

# Context - обмежений ресурс

---

<!-- .slide: data-background-color="#ffffff" -->

<span class="kicker">04</span>

# AGENTS.md

## <span data-sketch="circle-note" data-stroke="red" style="padding:2px 10px">Always-on</span> context

Note:
Перехід до конкретних інструментів guide. AGENTS.md — найбазовіший.

--

## Завжди в контексті

**Кожен** запит агента містить інструкції з `AGENTS.md`.

Тому ціна кожного рядка тут — висока.

--

<img src="img/nested-agents.svg" alt="Вкладені AGENTS.md: на кожному рівні директорій свій файл — агент бере найближчий + батьківські" style="width: 88%; max-height: 74vh; border: none; background: none; box-shadow: none;" />

--

<img src="img/agent-active-path.svg" alt="Активний шлях агента до змін; інші гілки задізейблені" style="width: 92%; max-height: 74vh; border: none; background: none; box-shadow: none;" />

--

## Два дослідження, що сперечаються

<div class="cols">
  <div class="card" data-sketch="box-fill" data-stroke="green" data-fill="green" data-hachure-gap="13" data-r="12">

### За

runtime **−28.6%**, output-токени **−16.6%**

→ швидше й дешевше
https://arxiv.org/pdf/2601.20404
  </div>
  <div class="card" data-sketch="box-fill" data-stroke="red" data-fill="red" data-hachure-gap="13" data-r="12">

### Проти

наявність файлу часто **−20% success rate**

overview = антипаттерн
https://arxiv.org/abs/2602.11988v1
  </div>
</div>

Note:
Чесно показати конфлікт. Висновок не "файл поганий", а "вміст вирішує": інструкції — так, оглядовий переказ репо — ні.

--

## Практика

- Checklist для `AGENTS.md`: інструкції, не переказ
- **Вкладені** `AGENTS.md` — локальний контекст там, де він потрібен

Note:
Вкладені файли — спосіб не роздувати кореневий: специфіка пакета лежить поруч із пакетом.

--

<span class="kicker">AGENTS.md · checklist</span>

<h2 style="color:#2f9e44; margin-bottom:0.1em">Що МАЄ бути</h2>

<div style="display:flex; gap:28px; align-items:stretch; margin-top:28px; text-align:left">
<div class="card" data-sketch="box" data-stroke="green" data-r="12" style="flex:1">

### Review Людиною, не ШІ

не `/init`, не автоген

<span class="muted">−3% success · +20% вартості</span>

</div>
<div class="card" data-sketch="box" data-stroke="green" data-r="12" style="flex:1">

### Лише мінімум

тільки найкритичніше для роботи з кодом

</div>
<div class="card" data-sketch="box" data-stroke="green" data-r="12" style="flex:1">

### Конкретний tooling

`uv` · `pytest` · `pdm` · скрипти репо

<span class="muted">найкорисніша частина</span>

</div>
</div>

Note:
1. Написано людиною, а не згенеровано ШІ — не /init. Згенеровані файли: −3% success rate, +20% вартості агента.
2. Лише мінімальні вимоги — тільки найкритичніше для роботи з кодом; необов'язкове лише ускладнює задачу.
3. Чітко вказаний tooling (uv, pytest, pdm, унікальні скрипти репо) — найкорисніша частина; агенти слухняно виконують прямі вказівки.

--

<span class="kicker">AGENTS.md · checklist</span>

<h2 style="color:#e03131; margin-bottom:0.1em">Чого НЕ треба</h2>

<div style="display:flex; gap:28px; align-items:stretch; margin-top:28px; text-align:left">
<div class="card" data-sketch="box" data-stroke="red" data-r="12" style="flex:1">

### Огляд структури репо

перелік директорій не допомагає — зайві кроки

</div>
<div class="card" data-sketch="box" data-stroke="red" data-r="12" style="flex:1">

### Дублювання доки

не копіюй `docs/`, інші `.md`, приклади коду

</div>
<div class="card" data-sketch="box" data-stroke="red" data-r="12" style="flex:1">

### Зайві «думати»-правила

стиль, дрібна архітектура

<span class="muted">+22% токенів роздумів</span>

</div>
</div>

<p class="muted" style="margin-top:30px; font-size:0.92em">Шпаргалка з кількох команд → лишаємо · схоже на сторінку документації → <span class="ds-mark">скоротити</span></p>

Note:
1. Огляди структури репо — не допомагають швидше знаходити файли; деякі моделі через них витрачають кроки на повторне перечитування цього ж файлу.
2. Дублювання документації — не копіюй docs/, інші .md, приклади коду; контекст-файли працюють як добра дока лише коли інших документів у репо нема.
3. Зайві правила стилю / другорядної архітектури → ШІ надмірно тестує, блукає по файлах, +22% "токенів роздумів" — дорожче, але не якісніше.
Головне правило валідації: якщо це шпаргалка з парою команд — ок; якщо повноцінна сторінка документації / архітектурний огляд — скоротити.

---

<!-- .slide: data-background-color="#ffffff" -->

<span class="kicker">05</span>

# Skills + Rules

`.md` файл + `frontmatter` (YAML з метаданими)

Note:
Обидва механізми — це просто markdown із YAML-шапкою. Різниця — коли і як вони потрапляють у контекст.

--

<img src="img/frontmatter-context.svg" alt="Зі skills/rules в always-on контекст потрапляє лише frontmatter; тіло — за потреби" style="width: 90%; max-height: 74vh; border: none; background: none; box-shadow: none;" />

--

## Rules — path-scoped контекст

- Прив'язані до **шляхів** (`path: ...`)
- Без path це фактично доповнення `AGENTS.md`
- Приклади з `catalog-ui`:
  - rule для GraphQL-фрагментів
  - правила оновлення доки
  - LSP-first для TypeScript · typed REST API

Note:
Головне про rules: завжди давати path. Інакше вони always-on і втрачають сенс. Показати, що саме потрапляє в контекст і коли.

--

## Skills — прописані workflow-патерни

Повторювані процедури, які агент має робити **однаково щоразу**.

- Приклади з `catalog-ui`:
  - skill для створення mr
  - skill для створення jira ticket

Note:
Skills — це "ось як ми тут робимо X". Підвантажуються за потреби, а не висять у контексті постійно.


---

<!-- .slide: data-background-color="#ffffff" -->

<span class="kicker">06 · 07</span>

# MCP + Plugins

Note:
Два зовнішні шари harness.

--

## MCP

Протокол для підключення зовнішніх тулзів і джерел.

`atlassian` · `context7`

Note:
MCP розширює, до чого агент має доступ: таски, доки, зовнішні API.

--

## Plugins

Набори скілів, хуків і скриптів для організації процесу.

**superpowers**: brainstorm · TDD · subagent · worktree · review

Note:
Плагіни пакують усталений процес. superpowers — приклад: цілий конвеєр розробки як набір скілів.

---

<!-- .slide: data-background-color="#ffffff" -->

<span class="kicker">08 · 09</span>

# Документація

## Пам'ять, яку агент може знайти

Note:
Доки — це довготривалий context, який не висить у вікні, але доступний за пошуком.

--

## Шари доки

- **spec** — як щось робили
- **ADR** — чому щось робили
- **docs/conventions** — конвенції рівня репозиторія
- **індекс доки** — спрощує пошук (README з посиланнями)

Note:
Розділення spec/ADR ключове: рішення (чому) живуть окремо від реалізації (як).

--

# Doc index

![doc-index](img/doc-index.png)
--

# /doc-capture skill

--

# ADR

## Architecture Decision Record

- Одне рішення = один файл. Короткий запис: контекст → рішення → наслідки.
- Ловить «чому». Код показує що зроблено; ADR пояснює, чому саме так і які альтернативи відкинули.
- Immutable. Рішення не редагують — застаріле помічають superseded новим ADR. Видно еволюцію думки.
- Для агента — це втрачений контекст. Без ADR агент не знає, що рішення навмисне, і «виправляє» його назад. З ADR — поважає межу.

--

## Інтеграція в catalog-ui

На *create-mr* skill додали перевірку чи потрібно додати *ADR*

--

![adr](img/adr.png)

--

# /propose-adr skill

---

<!-- .slide: data-background-color="#ffffff" -->

<span class="kicker">10</span>

# catalog-ui setup

--

<img src="img/skills-setup.svg" alt="Сетап скілів у catalog-ui: канон skills/ у корені + симлінки .claude/.cursor; рівні shared/local/global; Codex-виняток" style="width: 94%; max-height: 78vh; border: none; background: none; box-shadow: none;" />

--

## https://gitlab.evo.dev/ai-tools/ai-registry/-/tree/main/skills?ref_type=heads

<img src="img/skill-repo.png" alt="Сетап скілів у catalog-ui: канон skills/ у корені + симлінки .claude/.cursor; рівні shared/local/global; Codex-виняток" style="width: 94%; max-height: 78vh; border: none; background: none; box-shadow: none;" />

---

<!-- .slide: data-background-color="#ffffff" -->

<span class="kicker">11</span>

# Takeaway

--

<!-- .slide: data-background-color="#ffffff" -->

<img src="img/harness-loop.svg" alt="Цикл harness: агент → sensors → сигнал → guides → агент" style="width: 80%; max-height: 78vh; border: none; background: none; box-shadow: none;" />

--

# agent first flow

## AI agent - точка входу для будь якого workflow

- додай скіл
- додай rule
- як працює щось
- беремо задачу SHOPEX-34343 в роботу
- додаємо тест
... 

--

## Ключові думки

- Harness будують **інженери** — не модель
- Агент повторює помилку → сигнал **докрутити harness**
- Починай із **sensors**, потім **guides**

--


<!-- .slide: data-background-color="#ffffff" -->

# Дякую

https://t.me/ainomadic

![ainomad](img/ainomad.png)
