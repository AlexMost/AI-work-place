<!-- ───────────────────────── TITLE ───────────────────────── -->

<span class="kicker">інженерний клуб · SDD</span>

# Дві осі SDD

<p class="muted">специфікація і <span data-sketch="underline" data-stroke="orange">процес</span> — дві ортогональні осі під одним лейблом</p>

<div style="display:flex;gap:14px;justify-content:center;flex-wrap:wrap;margin-top:22px">
<span class="chip" data-sketch="box-fill" data-stroke="blue" data-fill="blue" data-r="9">spec axis</span>
<span class="chip" data-sketch="box-fill" data-stroke="orange" data-fill="yellow" data-r="9">process axis</span>
</div>

<p class="muted" style="margin-top:26px;font-size:0.7em">Олександр Мостовенко</p>

Note:
Жанр — «разом розбираємось», не «я навчу». Я в середині розбирання, ділюся тим, що зрозумів і де ще спотикаюсь. Аудиторія — інженери, overview AI-first не треба.

---

<!-- ───────────────────────── HOOK (3') ───────────────────────── -->

<span class="kicker">hook</span>

## Три години на вибір інструмента

<p class="muted">…і застряг на trade-off'ах, які насправді <span data-sketch="circle-note" data-stroke="red" style="padding:2px 10px">несумісні</span></p>

> Я склеїв **дві різні штуки** під одним словом — тому й буксував. Вони на різних осях.

Note:
Історія штормлення (доточити перед записом). Суть: порівнював речі, які не порівнюються, бо належать різним осям. Це і є спина всієї доповіді.

---

<!-- ───────────────────── БЛОК 0 — Підводка (7') ───────────────────── -->

<span class="kicker">0 · куди ми йдемо</span>

## Еволюція: vibe → agentic → loop

<div class="cols">
<div class="card">vibe coding<br/><span class="muted">чат, copy-paste</span></div>
<div class="card">agentic<br/><span class="muted">агент сам діє в репо</span></div>
<div class="card" data-sketch="box" data-stroke="ink" data-r="9">loop<br/><span class="muted">агент у циклі</span></div>
</div>

<p class="muted" style="margin-top:18px">важіль якості — не модель, а <span data-sketch="highlight" data-stroke="yellow">harness engineering</span></p>

Note:
Карпатий, коротко. Не переказувати весь шлях — лише вектор: важіль зміщується з моделі на те, що навколо неї. Spec і doc — частина harness. (тези 1, 2)

--

<span class="kicker">0 · ментальна модель</span>

## Синхронізувати себе з агентом

<div class="cols">
<div class="card">plan mode</div>
<div class="card">brainstorm</div>
<div class="card">grill-me</div>
</div>

<p class="muted" style="margin-top:20px">З чого складається harness? → дві осі</p>

Note:
Harness — наскрізний мотив, не окремий конкуруючий фрейм. Тут він підводить до питання «з чого harness складається», відповідь на яке — дві осі. Кульмінує в блоці 3. (теза 3)

---

<!-- ───────────────────── БЛОК 1 — Фрейм (5') ───────────────────── -->
<!-- ★ money-frame слайд -->

<span class="kicker">1 · фрейм</span>

## Дві ортогональні осі

<div class="cols">
<div class="card" data-sketch="box-fill" data-stroke="blue" data-fill="blue" data-r="9">
<strong>Spec axis</strong><br/>
<span class="muted">live specs = source-of-truth<br/>артефакти <em>durable</em></span><br/>
<span class="muted" style="font-size:0.8em">OpenSpec · Spec-Kit</span>
</div>
<div class="card" data-sketch="box-fill" data-stroke="orange" data-fill="yellow" data-r="9">
<strong>Process axis</strong><br/>
<span class="muted">plan + TDD + review per task<br/>артефакти <em>ephemeral</em></span><br/>
<span class="muted" style="font-size:0.8em">Superpowers · custom skills</span>
</div>
</div>

<p class="muted" style="margin-top:18px">Осі незалежні: можна одне, інше, обидва, або нічого</p>

Note:
Чому ортогональні, чому індустрія їх склеює. ОДРАЗУ проговорити явно: OpenSpec сидить на ОБОХ осях (живі specs + workflow propose→apply→archive) — це фіча, не баг. Інакше осі розмиваються саме тут.

---

<!-- ───────────────── БЛОК 2 — Process axis: Superpowers (7') ───────────────── -->

<span class="kicker">2 · process axis</span>

## Superpowers — перший крок до SDD

<p class="muted">має spec, але він про <span data-sketch="underline" data-stroke="orange">іншу вісь</span></p>

<div class="cols">
<div class="card">TDD</div>
<div class="card">review</div>
<div class="card">subagent-driven dev</div>
</div>

<p class="muted" style="margin-top:18px">Process discipline, <strong>не</strong> durable specs</p>

Note:
Чому process axis перший: простіший для входу. OpenSpec розкриваємо глибше потім. Superpowers має spec — але про процес, кращі практики, дисципліну, а не про живі специфікації. (теза 4)

---

<!-- ───────── БЛОК 3 — Spec axis: OpenSpec під капотом ⭐ (16') ───────── -->
<!-- серце deep-версії — третина доповіді, НЕ урізати -->

<span class="kicker">3 · spec axis ⭐</span>

## OpenSpec під капотом

<p class="muted">OpenSpec = можливість <span data-sketch="circle-note" data-stroke="red" style="padding:2px 10px">задати процес</span></p>

<p class="muted" style="margin-top:16px">далі — що саме <code>init</code> кладе в репо, і чому слеш-команда це просто промпт</p>

Note:
Серце deep-версії, ~16 хв. Тут найсильніша теза («harness росте з кожною таскою») + money shot. Не урізати. (тези 5–9)

--

<span class="kicker">3 · компоненти</span>

## Що `init` кладе в репо

```text
openspec/
  config.yaml
  specs/      ← живі специфікації (source-of-truth)
  changes/    ← активні зміни
.claude/commands/opsx/
  propose.md  apply.md  archive.md   ← слеш-команди = markdown
.claude/skills/openspec-*/SKILL.md
```

<p class="muted">жодного рантайму — лише артефакти + конвенція</p>

Note:
Розкриваємо капот: `ls openspec/` + `.claude/commands/opsx/`. OpenSpec нічого не приховує — оце все, що він додав. cli / commands / config.

--

<span class="kicker">3 · money shot 💰</span>

## Слеш-команда — це промпт у `.md`

<p class="muted"><code>/opsx:propose add-X</code> — не бінарник, а «підстав цей md-промпт у контекст агента»</p>

> Spec-driven = промпт-інженерія, **зафіксована в репозиторій**.

<p class="muted" style="margin-top:14px">я можу його <span data-sketch="highlight" data-stroke="yellow">читати, форкнути, підправити</span> під свій проєкт</p>

Note:
Момент демістифікації — тиснути на нього. Відкриваєш `.claude/commands/opsx/propose.md`: frontmatter (name, description) + тіло, яке і є промптом. Це акцент-якір на слайд.

--

<!-- DEMO: OpenSpec ~3' — відео ще не записане; sandbox = svadlenka-crm -->
<!-- .slide: data-background-color="#1e1e1e" -->

<span class="kicker" style="color:#ced4da">демо</span>

## ▶︎ OpenSpec на реальній задачі

<p style="color:#ced4da">propose → з'являються <code>proposal.md</code> · <code>design.md</code> · <code>tasks.md</code> · <code>specs/</code></p>

<p style="color:#868e96;margin-top:20px;font-size:0.7em">[ плейсхолдер під відео ~3' ]</p>

Note:
Шот-план у чернетці. Кадри: 1) розкриваємо капот 2) money shot — сам промпт 3) запуск /opsx:propose на дрібній фічі CRM 4) коротко apply 5) місток до тези. ⚠️ Перед записом: перевір `ls .claude/commands/` після init — точний неймспейс (opsx новий, є й legacy openspec).

--

<span class="kicker">3 · harness росте</span>

## Кожна таска синтезує знання

<div class="cols">
<div class="card">propose / apply<br/><span class="muted">+ кастомні артефакти<br/>(retrospective)</span></div>
<div class="card">verify / archive<br/><span class="muted">→ changes/archive/<br/>YYYY-MM-DD-add-X/</span></div>
</div>

<p class="muted" style="margin-top:18px">harness <span data-sketch="underline" data-stroke="green">росте</span> → наступна ітерація простіша</p>

Note:
Найсильніша теза блоку. Етапи propose/apply → кастомні артефакти → кожна таска додає знання в harness → наступна простіша. verify/archive фіксує результат у `changes/archive/`. Ще артефакти: ADR, doc indexes. (тези 7, 8, 9)

---

<!-- ─────────────── БЛОК 4 — Інтеграція осей + масштаб (8') ─────────────── -->

<span class="kicker">4 · інтеграція</span>

## Осі стекаються

<p class="muted">superpowers <strong>поверх</strong> openspec — напр. <code>grill-me-with-docs</code> замість brainstorm</p>

<div class="cols">
<div class="card" data-sketch="box-fill" data-stroke="blue" data-fill="blue" data-r="9">spec axis<br/><span class="muted">durable specs</span></div>
<div class="card" data-sketch="box-fill" data-stroke="orange" data-fill="yellow" data-r="9">process axis<br/><span class="muted">plan / TDD / review</span></div>
</div>

<p class="muted" style="margin-top:16px">ключовий кадр: <span data-sketch="circle-note" data-stroke="red" style="padding:2px 10px">передача контексту між осями</span></p>

Note:
Де spec закінчується, де процес починається. Що саме process layer тягне зі specs. Це найдорожчий кадр інтеграції. (тези 11, 10)

--

<!-- DEMO: інтеграція ~4' — відео ще не записане -->
<!-- .slide: data-background-color="#1e1e1e" -->

<span class="kicker" style="color:#ced4da">демо</span>

## ▶︎ Process layer поверх spec layer

<p style="color:#ced4da">spec уже існує → plan / TDD / review підхоплюють зі specs</p>

<p style="color:#868e96;margin-top:20px;font-size:0.7em">[ плейсхолдер під відео ~4' ]</p>

Note:
Той самий sandbox. Ключовий кадр — передача контексту між осями.

--

<span class="kicker">4 · масштаб</span>

## Агент — точка входу в проєкт

> Налаштував процес для агента = <span data-sketch="highlight" data-stroke="yellow">простіше скейлити на команду</span>

Note:
Агент = точка входу → той самий harness працює для кожного в команді → скейл. (теза 10)

---

<!-- ───────────── БЛОК 5 — Докази: svadlenka-crm (4') ───────────── -->

<span class="kicker">5 · докази</span>

## svadlenka-crm

<p class="muted">реальні результати по наявних артефактах</p>

<p class="muted" style="margin-top:18px;font-size:0.75em">[ конкретні приклади з репо — заповнити після прогону ]</p>

Note:
Реальні результати по артефактах зі svadlenka-crm. Альтернатива до окремого блоку — вплести живі приклади прямо в блок 3 (тоді цей блок зникає). Залежить від обсягу реального матеріалу. (теза 12)

---

<!-- ───────────────────────── LAND (3') ───────────────────────── -->

<span class="kicker">land</span>

## Питання, з яким лишаю зал

<p style="font-size:1.1em">Коли persistent specs варті <span data-sketch="circle-note" data-stroke="red" style="padding:2px 10px">своєї ціни</span>?</p>

<p class="muted" style="margin-top:14px">і як склеїти дві осі без redundancy?</p>

<p class="muted" style="margin-top:26px;font-size:0.7em">не вибирай SDD vs не-SDD — вибирай <strong>per axis</strong></p>

Note:
Відкрите питання залу, не відповідь. Headline takeaway обрати фінальний перед записом (кандидати в чернетці). Q&A — уточнити формат в організаторів.
