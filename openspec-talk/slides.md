
# Дві осі SDD

<p class="muted">специфікація і <span data-sketch="underline" data-stroke="orange">процес</span> — дві ортогональні осі</p>

<div style="display:flex;gap:14px;justify-content:center;flex-wrap:wrap;margin-top:22px">
<span class="chip" data-sketch="box-fill" data-stroke="blue" data-fill="blue" data-r="9">spec axis</span>
<span class="chip" data-sketch="box-fill" data-stroke="orange" data-fill="yellow" data-r="9">process axis</span>
</div>

<p class="muted" style="margin-top:26px;font-size:0.7em">Олександр Мостовенко</p>

Note:
Жанр — «разом розбираємось», не «я навчу». Я в середині розбирання, ділюся тим, що зрозумів і де ще спотикаюсь. Аудиторія — інженери, overview AI-first не треба.

---

<span class="kicker">about me</span>

## Олександр Мостовенко

<p class="muted">Software architect <span data-sketch="box" data-stroke="ink" data-r="8" style="padding:2px 10px">@ EVO</span></p>

<p class="muted fragment" style="margin-top:10px;font-size:0.8em">свій opensource → <a href="https://ttag.js.org/">ttag.js.org</a></p>

<p class="muted fragment" style="margin-top:10px;font-size:0.8em">github → <a href="https://github.com/AlexMost">https://github.com/AlexMost</a></p>

---

![prehistoric](img/prehistoric.png)

<p class="muted fragment" style="margin-top:24px">бачив .NET framework 3.5, Silverlight, joomla, python 2.6, flask, django, jquery, angular 1.5  </p>

---

# Дві осі SDD
## Spec Driven Development

---

# Agentic Engineering

---

# Vibe Coding

![Screenshot 2026-06-11 at 13.48.57.png](img/Screenshot%202026-06-11%20at%2013.48.57.png)

---

![Screenshot 2026-06-11 at 13.50.35.png](img/Screenshot%202026-06-11%20at%2013.50.35.png)

---

# Agentic Engineering

![Screenshot 2026-07-01 at 18.02.58.png](img/Screenshot%202026-07-01%20at%2018.02.58.png)

## https://www.youtube.com/watch?v=96jN2OCOfLs

---

# Головна мета "агентної інженерії"
## Полягає не просто у швидкості, а у збереженні <mark>високих стандартів</mark> професійного софту

---

![Screenshot 2026-07-01 at 18.34.24.png](img/Screenshot%202026-07-01%20at%2018.34.24.png)

## https://www.kaggle.com/whitepaper-the-new-SDLC-with-vibe-coding

---

![Screenshot 2026-07-01 at 18.35.12.png](img/Screenshot%202026-07-01%20at%2018.35.12.png)

---

![Screenshot 2026-07-01 at 18.36.11.png](img/Screenshot%202026-07-01%20at%2018.36.11.png)

---

![Screenshot 2026-07-01 at 18.41.02.png](img/Screenshot%202026-07-01%20at%2018.41.02.png)

## https://www.youtube.com/watch?v=v4F1gFy-hqg

---

![system.png](img/system.png)

---

![bigproject-good-architecture.png](img/bigproject-good-architecture.png)

---

## Agentic Engineering

<ul>
    <li class="fragment">Архітектура (System Design)</li>
    <li class="fragment">Кращі практики розробки (СI/CD, TDD, code review)</li>
    <li class="fragment">Harness Engineering</li>
</ul>

---

# Harness Engineering

![Screenshot 2026-06-11 at 23.58.12.png](img/Screenshot%202026-06-11%20at%2023.58.12.png)

## https://martinfowler.com/articles/harness-engineering.html

---

![img.png](img/img.png)

---

![harness-engineering.png](img/harness-engineering.png)

---

## Дві осі SDD

![two-axes](img/two-axes.png)

---

# Process axis
## superpowers

---

# Plan

<ul>
    <li class="fragment">Plan mode</li>
    <li class="fragment">/superpowers:brainstorming</li>
    <li class="fragment">/grill-me</li>
</ul>

---

# Синронізація ментальної моделі

![design-concept.png](img/design-concept.png)

---

# Context engineering

![agent-context-search.png](img/agent-context-search.png)

---

# TDD
## superpowers:test-driven-development
## tdd mattpocock

---

# Parallel execution (orchestration)
## superpowers:subagent-driven-development

---

# Code review
## superpowers:subagent-driven-development

---

# Spec axis

---

# Openspec

## https://openspec.dev/
---

![openspec-state-machine.png](img/openspec-state-machine.png)

---

# superpowers spec != openspec spec.md

---

# superpowers spec.md plan.md
## Актуальні під час виконання задачаі

---

# Openspec під капотом

<ul>
    <li class="fragment">openspec cli - prompt generator + state machine</li>
    <li class="fragment">agent skills/commands</li>
</ul>

---

# openspec init

---

## /opsx:propose -> /opsx:apply -> /opsx:verify -> /opsx:archive

---

# /opsx:propose

![openspec-propose.png](img/openspec-propose.png)

---

# /opsx:apply

![openspec-apply.png](img/openspec-apply.png)

---

## worktree

![Screenshot 2026-06-12 at 9.47.45.png](img/Screenshot%202026-06-12%20at%209.47.45.png)

---

# /opsx:verify

![openspec-verify.png](img/openspec-verify.png)

---

# /opsx:archive

![openspec-archive.png](img/openspec-archive.png)

---

![Screenshot 2026-07-01 at 22.08.38.png](img/Screenshot%202026-07-01%20at%2022.08.38.png)

---

![Screenshot 2026-07-01 at 22.10.19.png](img/Screenshot%202026-07-01%20at%2022.10.19.png)

---

<span class="kicker">spec axis</span>

# Оновлення специфікації

<p class="muted">зміна не переписує спеку — вона описує <span data-sketch="underline" data-stroke="orange">дельту</span></p>

Note:
Ключова ідея spec-осі: коли зміна чіпає поведінку, вона не редагує канонічну спеку напряму. Вона кладе delta-файл — набір операцій над вимогами. Канонічна спека оновлюється лише на archive.

---

## Дельта-операції

<ul>
  <li class="fragment"><code>ADDED</code> — нова вимога</li>
  <li class="fragment"><code>MODIFIED</code> — змінена, з <b>повним</b> новим текстом</li>
  <li class="fragment"><code>REMOVED</code> — прибрана, з <code>Reason</code> + <code>Migration</code></li>
  <li class="fragment"><code>RENAMED</code> — <code>FROM:</code> / <code>TO:</code></li>
</ul>

<p class="muted fragment" style="margin-top:18px">delta = контракт зміни, а не diff</p>

---

<span class="kicker">openspec archive</span>

## Дельта → жива спека

<div class="cols">
<div class="card">
<b>дельта зміни</b>
<p class="muted" style="font-size:0.8em">changes/…/specs/auth-google/spec.md</p>
<span data-sketch="box" data-stroke="orange" data-r="8" style="display:inline-block;padding:2px 10px">ADDED · MODIFIED · REMOVED</span>
</div>
<div class="card">
<b>канонічна спека</b>
<p class="muted" style="font-size:0.8em">specs/auth-google/spec.md</p>
<span data-sketch="box" data-stroke="blue" data-r="8" style="display:inline-block;padding:2px 10px">8 вимог, без маркерів</span>
</div>
</div>

<p class="fragment" style="margin-top:22px">жива спека = <mark>сума застосованих дельт</mark></p>

Note:
На archive CLI зливає дельти в openspec/specs/<capability>/spec.md. У канонічній спеці вже НЕМАЄ маркерів ADDED/MODIFIED/REMOVED — тільки поточний стан. Приклад: «Role assigned from allowlist config» тепер живе в specs/auth-google/spec.md, а «Hardcoded operator role» звідти зникла.

---

<span class="kicker">spec axis · CI</span>

# Спека — машинно-перевірювана

<p class="muted">merge-гейт: невалідна спека → <span data-sketch="underline" data-stroke="orange">червоний CI</span></p>

<p class="fragment" style="margin-top:18px"><code>openspec validate --all --strict</code></p>

<p class="muted fragment" style="margin-top:14px">exit ≠ 0 — PR не мержиться</p>

Note:
CI-рецепт (GitHub Actions, один крок):
  - run: npx @fission-ai/openspec@latest validate --all --strict
Що ловить: Scenario не з 4 решіток (#### — інакше тихо ігнориться), вимога без SHALL/MUST, вимога без жодного сценарію, битий delta-хедер. Команда виставляє exitCode=1 і робить process.exit → чесно валить білд. Це та сама перевірка, що verify.md §1 робить усередині workflow (`openspec validate --all --json`), тільки на CI вона не залежить від агента.

---

## «Всі зміни зроблені» = 3 рівні

<ul>
  <li class="fragment"><b>структура</b> — <code>openspec validate --all --strict</code></li>
  <li class="fragment"><b>таски</b> — у tasks.md не лишилось <code>- [ ]</code></li>
  <li class="fragment"><b>архів</b> — дельти влиті в <code>specs/</code>, немає висячих changes</li>
</ul>

<p class="muted fragment" style="margin-top:18px">verify-фаза кодифікує всі три в самому workflow</p>

Note:
Рівень 1 — вбудований чистий CI-гейт. Рівні 2-3 — простий grep у CI: незакриті чекбокси в openspec/changes/*/tasks.md (поза archive/) або наявність незаархівованої зміни = «ще не готово, не мерж». У superpowers-bridge усі три вже зашиті у verify.md (§1 validate, §2 task completion, §3 delta-sync) + config rules.verify з репо-гейтами (pnpm test / lint / typecheck / format:check). Тобто те, що агент робить у verify-артефакті, CI дублює як незалежний страж перед мержем.

---

![Screenshot 2026-07-02 at 16.28.39.png](img/Screenshot%202026-07-02%20at%2016.28.39.png)

---
![openspec-process-1.png](img/openspec-process-1.png)

---

## worktree

![Screenshot 2026-06-12 at 9.47.45.png](img/Screenshot%202026-06-12%20at%209.47.45.png)

---

# Openspec + superpowers
https://github.com/JiangWay/openspec-schemas/tree/main/superpowers-bridge

---

<span class="kicker">висновок</span>

## Дві осі — це один harness

<div class="cols">
<div class="card">
<b>spec axis</b>
<p class="muted" style="font-size:0.8em">що і чому</p>
<span data-sketch="box" data-stroke="blue" data-r="8" style="display:inline-block;padding:2px 10px">docs · specs · ADR</span>
</div>
<div class="card">
<b>process axis</b>
<p class="muted" style="font-size:0.8em">як і наскільки добре</p>
<span data-sketch="box" data-stroke="orange" data-r="8" style="display:inline-block;padding:2px 10px">plan · TDD · review</span>
</div>
</div>

<p class="fragment" style="margin-top:22px">не бюрократія — <mark>середовище, у якому агент працює ефективно</mark></p>

Note:
Повернення до тези відкриття: дві ортогональні осі. Тепер зводимо їх в одне ім'я — harness. Це той самий Harness Engineering з початку доповіді, тільки конкретно: спека-вісь дає агенту «що і чому», процес-вісь — «як і наскільки добре».

---

## Чому harness підсилює агента

<ul>
  <li class="fragment"><b>specs / ADR</b> — пам'ять агента між сесіями: що і чому</li>
  <li class="fragment"><b>plan / TDD / review</b> — планка якості, винесена з голови сеньйора назовні</li>
  <li class="fragment">без harness агент щоразу <b>перевигадує контекст</b> і дрейфує</li>
</ul>

<p class="muted fragment" style="margin-top:18px">harness = зовнішній контекст + зовнішня дисципліна</p>

Note:
Ключовий інсайт доповіді. Агенту вроджено бракує двох речей: пам'яті між сесіями і власної планки якості. Harness дає обидві — специфікації/ADR як зовнішня пам'ять, TDD/review/plan як зовнішня дисципліна. Те, що сеньйор тримає в голові, ми виносимо назовні у файли — і тоді на цю базу може стати будь-який агент у будь-якій сесії.

---

# conductor -> orchestrator

![harness-engineering-1.png](img/harness-engineering-1.png)

## https://www.kaggle.com/whitepaper-the-new-SDLC-with-vibe-coding

---

# Дякую
## Ділюсь думками про AI інженерію тут

<div style="display:flex;align-items:center;justify-content:center;gap:48px;margin-top:14px">
<img src="img/tg-ainomadic.svg" alt="QR — t.me/ainomadic" style="width:260px;height:260px" />
<div style="text-align:left">
<span data-sketch="box-fill" data-stroke="blue" data-fill="blue" data-r="9" style="display:inline-block;padding:6px 16px;font-family:var(--font-hand)">@ainomadic</span>
<p class="muted" style="margin-top:18px">Олександр Мостовенко<br/><a href="https://t.me/ainomadic">t.me/ainomadic</a></p>
</div>
</div>

Note:
Фінальний слайд під Q&A — QR лишається на екрані поки йдуть питання, встигнуть відсканувати.
