# CSS-анімації плиток — Resources

## Knowledge

- [Josh Comeau — An Interactive Guide to CSS Transitions](https://www.joshwcomeau.com/animation/css-transitions/) ✅ перевірено
  Найкращий вступ для початківця: інтерактивний, на живих прикладах пояснює
  `transition`, easing, timing, чому `transform`/`opacity` дешеві, `prefers-reduced-motion`.
  **Use for:** уроки про slide (0001) та easing (0002). Це primary source.
- [MDN — Using CSS transitions](https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_transitions/Using_CSS_transitions)
  Канонічна довідка: синтаксис, які властивості анімуються, `transition-*` підвластивості.
  **Use for:** точний синтаксис, перевірка фактів.
- [MDN — Using CSS animations (@keyframes)](https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_animations/Using_CSS_animations)
  Довідка по `@keyframes`, `animation-*`, `animation-fill-mode`.
  **Use for:** урок про pop/appear/merge (0003).
- [MDN — transform](https://developer.mozilla.org/en-US/docs/Web/CSS/transform)
  Чому `transform` не зачіпає layout і дешевий для анімації.
  **Use for:** урок про slide (0001).
- [web.dev — Animations guide](https://web.dev/articles/animations-guide)
  Чому анімувати `transform`/`opacity`, а не `left`/`top`/`width`.
  **Use for:** performance, чому саме transform.

## Wisdom (Communities)

- [r/css](https://www.reddit.com/r/css/) та [r/Frontend](https://www.reddit.com/r/Frontend/)
  Можна показати свій pen/демо і отримати критику. **Use for:** фідбек на власні анімації.
- [CodePen](https://codepen.io/) — пошук "2048", "tile slide", "FLIP animation"
  Розбирати чужі live-приклади і форкати. **Use for:** вчитися на реальних реалізаціях.

## Gaps
- Треба знайти й **перевірити URL** першоджерела по FLIP-техніці (Paul Lewis,
  «FLIP your animations») перед уроком 0004 — не цитувати з пам'яті.
