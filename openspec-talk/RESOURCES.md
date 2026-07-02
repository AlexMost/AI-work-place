# OpenSpec internals + superpowers-bridge — Resources

## Knowledge

- [Сирці: Fission-AI/OpenSpec (GitHub)](https://github.com/Fission-AI/OpenSpec)
  Першоджерело №1 — код CLI (`@fission-ai/openspec`). Use for: будь-яке твердження про механіку CLI (резолвінг схем, prompt compiler, DAG). Клонувати в scratchpad: `git clone --depth 1 https://github.com/Fission-AI/OpenSpec.git`.
- [Сирці: JiangWay/openspec-schemas (GitHub)](https://github.com/JiangWay/openspec-schemas)
  Репо схеми `superpowers-bridge` (v1, baseline: OpenSpec CLI 1.4.1 + superpowers v5.1.0). README на 544 рядки — головне джерело по design-рішеннях bridge (PRECHECK-патерн, fail-loud, no-executing-plans-fallback, timing mismatch verify/retrospective). Use for: усе про bridge.
- Живий артефакт: `~/git/svadlenka-crm/openspec/`
  Встановлена копія bridge (`schemas/superpowers-bridge/schema.yaml`, ≈ upstream v1) + проєктний `config.yaml` з per-artifact `rules:` (design→ADR, tasks→TDD-friendly units, verify→гейти). Use for: як проєкт нашаровує свої правила поверх схеми, не форкаючи її.
- Локальні сирці superpowers: `~/git/superpowers/skills/`
  Скіли obra/superpowers. Ключове: `subagent-driven-development/SKILL.md:272-276` — транзитивна активація `test-driven-development` і `requesting-code-review`. Use for: перевірка, що саме «приносить» кожен скіл в apply-фазу.
- `demo.md` (цей репо)
  Сценарій live-демо доповіді (написаний агентом, перевірений на openspec 1.3.1). Use for: які команди показуємо залу; НЕ як джерело істини про internals.

## Wisdom (Communities)

- [GitHub Discussions/Issues: Fission-AI/OpenSpec](https://github.com/Fission-AI/OpenSpec/issues)
  Місце, де мейнтейнери відповідають на питання про механіку і roadmap (напр., ідея `post_apply`-фази). Use for: перевірити, чи «дірка», яку ти знайшов, відома; спитати про extension points.
- Інженерний клуб (доповідь «Дві осі SDD»)
  Q&A після доповіді — головний реальний тест розуміння. Use for: збір питань, на які не було відповіді → нові learning records.

## Gaps

- Немає перевіреного чату/Discord спільноти OpenSpec — перевірити, чи існує офіційний (README репо).
- Немає незалежних розборів internals OpenSpec (блог-постів рівня «як влаштований X») — поки що єдине джерело = сирці.
