# Teaching notes

## Профіль учня
- Senior JS/TS інженер; вільно читає TypeScript-сирці. Пояснення «для початківців» — зайві.
- Мова спілкування і матеріалів — українська; код/цитати — мовою оригіналу.
- Вже активно ВИКОРИСТОВУЄ OpenSpec 1.3.x + superpowers-bridge у продакшн-репо (`~/git/svadlenka-crm`). ZPD = рівень сирців і механіки, не рівень «як користуватись».
- ВАЖЛИВО: `demo.md` і трирівневу тезу в ньому писав агент у попередній сесії, НЕ учень (учень явно уточнив). Тези доповіді ≠ засвоєні знання — їх треба ВЧИТИ, а не пропускати як відомі.

## Преференції
- Вчити на першоджерелах з точними цитатами `file:line` — ніяких переказів з пам'яті.
- Прив'язувати уроки до доповіді: кожен інсайт має підсилювати демо №1 (CLI під капотом) або демо №2 (bridge).
- Живі артефакти для практики: `~/git/svadlenka-crm/openspec/` (config.yaml + schemas/superpowers-bridge/schema.yaml).

## Робочі нотатки
- Сирці для навчання клонуються у scratchpad сесії (шлях змінюється щосесії): `git clone --depth 1 https://github.com/Fission-AI/OpenSpec.git`, `git clone --depth 1 https://github.com/JiangWay/openspec-schemas.git`.
- Схема в svadlenka-crm ≈ upstream JiangWay v1 (та сама структура: verify §1-7, retrospective §0-6, apply кроки 0-6; line numbers збігаються). Upstream README (544 рядки) — основне джерело по design-рішеннях bridge.
- Цей workspace = репо доповіді. lessons/assets/reference співіснують зі slides.md — не чіпати talk-файли без потреби.
