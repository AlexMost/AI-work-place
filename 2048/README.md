# 2048 · neon

Браузерна гра 2048 на TypeScript + Vite, без фреймворків. Неоновий glassmorphism-стиль, анімовані переходи плиток (slide / merge-pop / glow), керування клавіатурою (стрілки / WASD) і свайпом на мобільному.

Натхнення — [старий ELM-варіант](https://github.com/AlexMost/2048), логіка переписана з нуля.

## Запуск

```bash
npm install
npm run dev      # локальний дев-сервер
npm run build    # tsc + продакшн-збірка у dist/
npm run preview  # переглянути збірку
```

## Деплой

```bash
npm run publish-gh-pages
```

Публікує `dist/` у підкаталог `2048/` гілки `gh-pages`.
URL: https://alexmost.github.io/AI-work-place/2048/

## Структура

- `src/game.ts` — чиста ігрова логіка (сітка, рух, злиття, спавн). Кожна плитка має стабільний `id` і `prev`-позицію, щоб рендер міг анімувати переходи.
- `src/render.ts` — DOM-рендер плиток, рахунку та оверлеїв.
- `src/input.ts` — клавіатура + свайп (touch).
- `src/main.ts` — звʼязує все докупи, зберігає рекорд у `localStorage`.
- `src/style.css` — неоновий стиль і анімації.
