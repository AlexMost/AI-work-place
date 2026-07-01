# Демо: OpenSpec CLI під капотом (~3')

Шпаргалка для live-демо в блоці 3. Усе працює з чистої теки, без інсталяції (`npx`).
Перевірено на `@fission-ai/openspec` **1.3.1**.

## Теза демо

Промпти OpenSpec живуть у **трьох шарах**, і всі три можна просто відкрити й прочитати:

1. **Слеш-команди = markdown-файли** у `.claude/commands/opsx/` — жодної магії.
2. **CLI = детермінований state machine** без жодного LLM-виклику: скафолдинг, DAG артефактів, JSON для агента.
3. **`openspec instructions` = prompt compiler**: schema + template + config.yaml → один готовий промпт для агента.

## Сценарій (команди по черзі)

```bash
mkdir opsx-demo && cd opsx-demo && git init

# 1. init створює ВСЬОГО дві речі: openspec/config.yaml + 8 слеш-команд
npx @fission-ai/openspec@latest init --tools claude .
find . -type f -not -path "./.git/*"

# 2. Money shot: слеш-команда — це просто промпт у .md (~100-170 рядків кожна)
cat .claude/commands/opsx/propose.md

# 3. CLI-команди, які ці промпти викликають за даними
npx openspec new change demo-feature

# 4. DAG артефактів — CLI тримає стан, а не «думає»
npx openspec status --change demo-feature
```

Очікуваний вивід `status`:

```
Progress: 0/4 artifacts complete
[ ] proposal
[-] design (blocked by: proposal)
[-] specs  (blocked by: proposal)
[-] tasks  (blocked by: design, specs)
```

```bash
# 5. Промпт, який CLI «генерує» для конкретного артефакту
npx openspec instructions proposal --change demo-feature
```

Вивід — enriched-промпт, скомпонований CLI:

- `<task>` — що зробити
- `<output>` — точний шлях файлу, куди писати
- `<instruction>` — інструкція зі схеми (`spec-driven`)
- `<template>` — структура файлу
- `<unlocks>` — які артефакти розблокуються далі (`design`, `specs`)
- сюди ж підмішуються `context:` і `rules:` з `openspec/config.yaml`

```bash
# 6. Бонус: схеми в репо не копіюються — вбудована живе в npm-пакеті
npx openspec templates
# Source: package
# proposal: ~/.npm/_npx/.../schemas/spec-driven/templates/proposal.md
```

## Корисні команди для «подивитись промпти» (довідково)

| Команда | Що показує |
| --- | --- |
| `cat .claude/commands/opsx/<cmd>.md` | промпт слеш-команди як є |
| `openspec instructions <artifact> --change <name>` | скомпонований промпт для артефакту (є `--json`) |
| `openspec status --change <name> [--json]` | DAG артефактів, що заблоковано чим |
| `openspec templates` | resolved-шляхи темплейтів (package vs override у репо) |
| `openspec schemas --json` | доступні workflow-схеми |

## Демо №2: інтеграція superpowers + openspec (~4', блок 4)

Живий артефакт — кастомна схема в `svadlenka-crm`:

```bash
cd ~/git/svadlenka-crm
cat openspec/schemas/superpowers-bridge/schema.yaml   # схема, де кожен artifact.instruction викликає superpowers-скіл
cat openspec/config.yaml                              # проєктні rules per-artifact (design→ADR, tasks→TDD, verify→gates)
ls openspec/changes/archive                           # «harness виріс за N ітерацій»
```

Ключові кадри:

- `schema.yaml`: артефакт `brainstorm` → `Skill: superpowers:brainstorming`, apply-фаза → worktrees + `subagent-driven-development` (TDD і code review приходять транзитивно).
- `config.yaml` → `rules:` — як проєкт додає свої вимоги до кожного артефакту, не форкаючи промпти.
- Це і є «передача контексту між осями»: process axis (superpowers) виконується всередині workflow spec axis (openspec).
