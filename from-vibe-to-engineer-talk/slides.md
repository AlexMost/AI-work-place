<!-- .slide: data-background-image="img/bg/title.jpg" -->

<!-- титульний слайд івенту — чистий фірмовий фон -->

Note:
Привітання. Це слайд-обкладинка івенту, на ньому нічого не кажемо — одразу перемикаємось на представлення.

---

<span class="kicker">evo AI DAY · 12 червня</span>

# Від вайбкодінгу до Агентної інженерії

<p class="muted">чому якість софту визначає процес, а не модель</p>

<p style="margin-top:1.6em">Олександр Мостовенко</p>

Note:
Хто я, чим займаюсь, чому ця тема. Одне речення про контекст: останній місяць будую робочі флоу з AI-агентами і хочу поділитись, що з цього вийшло.

---

## Трохи історії

---

![gpt.png](img/content/gpt.png)

---

![gpt-calculate.png](img/content/gpt-calculate.png)

---

![cot.png](img/content/cot.png)

---

# Chain of Thought (CoT)

## https://arxiv.org/abs/2201.11903

---

# CoT, ToT, ReAct...

---

# Agent

---

![agent.png](img/content/agent.png)

---

<img class="plain" src="img/diagrams/agent-loop.svg" style="max-height:560px" />

---

<img class="plain" src="img/diagrams/chat-to-agent.svg" style="max-height:560px" />

---

# Вайбкодінг

---

![Screenshot 2026-06-11 at 13.48.57.png](img/content/Screenshot%202026-06-11%20at%2013.48.57.png)

https://x.com/karpathy/status/1886192184808149383?s=20

---

![Screenshot 2026-06-11 at 13.52.13.png](img/content/Screenshot%202026-06-11%20at%2013.52.13.png)

---

![Screenshot 2026-06-11 at 13.54.23.png](img/content/Screenshot%202026-06-11%20at%2013.54.23.png)

---

# Переваги vibe coding

<ul>
<li class="fragment">інструмент, який <mark>прибирає бар'єр</mark> — поекспериментувати, запустити, перевірити ідею</li>
<li class="fragment">без команди, без бюджету, без занурення в стек</li>
</ul>

Note:
Посил: це мега круто. Людина без техбекграунду (або інженер без вільного вечора) втілює ідею одразу, поки вона жива. Бар'єр, який раніше складався з команди, бюджету і тижнів сетапу, стиснувся до промпта. Звідси міст до наступного слайда: чому ж тоді це не скрізь працює.

---

## Від думки до реалізації відділяють лише токени та здатність сформулювати ідею

---

## Ви самі маючи ідею і бачення краще знаєте який продукт хочете побудувати

---

# Engineering solved?

---

![image-vibe.png](img/content/image-vibe.png)

---

![image-vibecode-angry.png](img/content/image-vibecode-angry.png)

---

## Не роби помилок!

---

## Не роби багів!

---

## Не роби багів!!!

---

## Ти найдосвідченіший розробник на планеті!!! 
## маєш 30 років досвіду роботи...

---

## маєш 3000 років досвіду роботи!!!

---

![agent-frustrated.png](img/content/agent-frustrated.png)

---

## Чому так відбувається?

---

![small-vs-big-project.png](img/content/small-vs-big-project.png)

---

![image-software-dev.png](img/content/image-software-dev.png)

---

![system.png](img/content/system.png)

---

![Screenshot 2026-06-11 at 19.24.48.png](img/content/Screenshot%202026-06-11%20at%2019.24.48.png)

---

# Software Entropy

---

## Софт сам по собі не стає простішим. Без постійного догляду він стає складнішим.

- David Thomas & Andrew Hunt

---

# Context engineering

![agent-context-search.png](img/content/agent-context-search.png)

---

# Lost in the Middle: How Language Models Use Long Contexts

## https://arxiv.org/pdf/2307.03172
---

# Context - обмежений ресурс

---

![bigproject-good-architecture.png](img/content/bigproject-good-architecture.png)

---

![system.png](img/content/system.png)

---

![Screenshot 2026-06-11 at 16.55.29.png](img/content/Screenshot%202026-06-11%20at%2016.55.29.png)

## John Ousterhout

---

# «Складність — це будь-що, пов’язане зі структурою програмної системи, що робить важким розуміння та модифікацію системи».
## - John Ousterhout

---

# Code is cheap
![Screenshot 2026-06-11 at 19.30.22.png](img/content/Screenshot%202026-06-11%20at%2019.30.22.png)
https://www.youtube.com/watch?v=v4F1gFy-hqg

---

# Code * Fail risk = $

---

![bad-code-production.png](img/content/bad-code-production.png)

---

![Screenshot 2026-06-11 at 19.34.42.png](img/content/Screenshot%202026-06-11%20at%2019.34.42.png)

---

![Screenshot 2026-06-11 at 21.16.53.png](img/content/Screenshot%202026-06-11%20at%2021.16.53.png)

---

![Screenshot 2026-06-12 at 9.04.42.png](img/content/Screenshot%202026-06-12%20at%209.04.42.png)

---

# Agentic Engineering

![Screenshot 2026-06-11 at 21.10.25.png](img/content/Screenshot%202026-06-11%20at%2021.10.25.png)

https://www.youtube.com/watch?v=96jN2OCOfLs

---

# Головна мета "агентної інженерії"
## Полягає не просто у швидкості, а у збереженні <mark>високих стандартів</mark> професійного софту

---

# Людина має "залишатися в циклі"
## Моделі бувають непередбачуваними у своїх можливостях, тому їх треба сприймати як <mark>інструменти</mark> і постійно стежити за їхніми діями

---

# Відповідальність за архітектуру <mark>лежить на людині</mark>
## Людина має повністю відповідати за специфікації, план розробки, дизайн та інженерний смак

---

# ШІ погано справляється з архітектурою
## Карпатий зізнається, що іноді згенерований код викликає у нього "серцевий напад", оскільки він може працювати, але при цьому бути дуже роздутим, містити "незграбні абстракції, які є крихкими"

---

![Screenshot 2026-06-11 at 23.53.45.png](img/content/Screenshot%202026-06-11%20at%2023.53.45.png)

---

## Agent - надзвичайно здібний стажер який не втомлюється і завжди готовий до виконання задач.

---

# Швидкість vs Якість

---

## Чому агент помиляється?

---

## AI зробив не те що я просив

---

# No-one knows exactly what they want

- David Thomas & Andrew Hunt (Pragmatic Programmer)

---

![design-concept.png](img/content/design-concept.png)

---

# Синхронізація ментальної моделі

Note:
Проблема не нова (no-one knows exactly what they want) — AI її лише загострив: ціна розбіжності впала з тижнів до хвилин, тому узгоджувати картини треба ДО коду. Міст до plan mode: саме тому в агентах це вбудований режим, а не звичка ентузіастів.

---

# Plan mode

![Screenshot 2026-06-11 at 21.30.46.png](img/content/Screenshot%202026-06-11%20at%2021.30.46.png)

---

# /superpowers:brainstorming
# /grill-me
# /grill-me-with-docs

---

![specs.png](img/content/specs.png)

---

![duck.png](img/content/duck.png)

Note:
Раніше пояснював задачу качечці — інсайт був випадковим. Тепер качечка відповідає і допитує. Перший ефект формалізації: поки не сів формулювати — здається, що все ясно; питання агента показують, що ні.

---

# Agent = Harness + LLM

---

## Harness Engineering

![Screenshot 2026-06-11 at 23.58.12.png](img/content/Screenshot%202026-06-11%20at%2023.58.12.png)

---

<img class="plain" src="img/diagrams/sensors-guides-rails.svg" style="max-height:560px" />

---

![guides.png](img/content/guides.png)

---

![sensors.png](img/content/sensors.png)

---

# TDD

---

# superpowers:tdd

---

## superpowers:subagent-driven-development

![specs.png](img/content/specs.png)

---

# Core principle
## Fresh subagent per task + two-stage review 
## (spec then quality) = high quality, fast iteration

---

# SDD (OpenSpec)
## https://github.com/Fission-AI/OpenSpec/

---

![openspec.png](img/content/openspec.png)

---

# OpenSpec + Superpowers

<ul>
    <li class="fragment">Синхронізація ментальної моделі</li>
    <li class="fragment">Кращі практики розробки вшиті в процесс</li>
    <li class="fragment">Можливість налаштовувати/впроваджувати процесс</li>
    <li class="fragment">Автооновлення документації</li>
    <li class="fragment">Системне покращення Harness</li>
</ul>

---

# Agent native / Agent first

---

![agentic-first.png](img/content/agentic-first.png)

---

![bigproject-good-architecture.png](img/content/bigproject-good-architecture.png)

---

![Screenshot 2026-06-12 at 7.59.25.png](img/content/Screenshot%202026-06-12%20at%207.59.25.png)

---

![Screenshot 2026-06-12 at 7.43.22.png](img/content/Screenshot%202026-06-12%20at%207.43.22.png)

---

![Screenshot 2026-06-12 at 7.44.06.png](img/content/Screenshot%202026-06-12%20at%207.44.06.png)

---

![Screenshot 2026-06-12 at 9.47.45.png](img/content/Screenshot%202026-06-12%20at%209.47.45.png)

---

## Простіше/швидше самому?

<ul>
    <li class="fragment">Тести</li>
    <li class="fragment">Документація</li>
    <li class="fragment">Моніторинг CI</li>
    <li class="fragment">Оновлення задачі в jira</li>
</ul>

---

# Loops

---

![harness-engineering.png](img/content/harness-engineering.png)

---
- https://ghuntley.com/loop/
- https://addyosmani.com/blog/loop-engineering/
- https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents
- https://www.anthropic.com/engineering/harness-design-long-running-apps
- https://openai.com/uk-UA/index/harness-engineering/
---

# Висновки

<ul>
    <li class="fragment">Концентруйтесь на можливостях</li>
    <li class="fragment">Будуйте процес</li>
    <li class="fragment">Баланс якість vs швидкість</li>
    <li class="fragment">Інженер відповідальний за архітектуру і якість</li>
    <li class="fragment">Людина — в центрі архітектури, як <mark>диригент</mark>: агенти грають, ви тримаєте задум і темп</li>
</ul>

Note:
Фінальний образ: harness — це оркестр. Агенти — виконавці, sensors і guides — партитура, але диригент — людина: задає задум, тримає темп, чує, коли хтось фальшивить. Без диригента оркестр грає голосно, але не музику. Це відповідь і на «engineering solved?» з початку — ні, роль інженера не зникла, вона піднялася на рівень вище.

---

# Відкриті питання

<ul>
    <li class="fragment">Вартість agent first систем</li>
    <li class="fragment">Вимірювання загальної ефективності системи</li>
    <li class="fragment">Безпека</li>
</ul>

---

# Дякую!

## https://t.me/ainomadic

![ainomad.png](img/content/ainomad.png)
