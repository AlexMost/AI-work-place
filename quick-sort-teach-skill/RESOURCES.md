# Quicksort Resources

## Knowledge

- [Book: _Introduction to Algorithms_ (CLRS), Ch. 7 "Quicksort" — Cormen, Leiserson, Rivest, Stein](https://mitpress.mit.edu/9780262046305/introduction-to-algorithms/)
  Канонічний першоджерельний виклад: Lomuto partition, аналіз середнього та гіршого випадку, randomized quicksort. Use for: формальний доказ складності, інваріант партиціювання.
- [MIT 6.006 — Lecture on Quicksort / Randomized algorithms (OpenCourseWare)](https://ocw.mit.edu/courses/6-006-introduction-to-algorithms-spring-2020/)
  Безкоштовні лекції + конспекти від MIT. Use for: інтуїція рекурсії та чому рандомізація рятує від O(n²).
- [Sedgewick & Wayne — _Algorithms_ (Princeton), Quicksort section + booksite](https://algs4.cs.princeton.edu/23quicksort/)
  Hoare-схема партиціювання, чудові візуалізації, готовий код. Use for: альтернативна (двостороння) схема партиціювання та практичні деталі.
- [Wikipedia: Quicksort](https://en.wikipedia.org/wiki/Quicksort)
  Добре відмодерована оглядова стаття: історія (Tony Hoare, 1959/1961), Lomuto vs Hoare, варіанти вибору pivot. Use for: швидкий огляд і термінологія.
- [TypeScript Handbook](https://www.typescriptlang.org/docs/handbook/intro.html)
  Офіційна довідка по мові. Use for: типізація функцій, generics, tuple-деструктуризація для swap.

### TypeScript Generics

- [TypeScript Handbook — Generics](https://www.typescriptlang.org/docs/handbook/2/generics.html)
  Канонічне першоджерело: generic-функції, constraints (`extends`), generic-класи, дефолти. Use for: точні означення й офіційний синтаксис.
- [TypeScript Handbook — Type Inference](https://www.typescriptlang.org/docs/handbook/type-inference.html)
  Як TS виводить типи на місці виклику. Use for: розуміння, чому не треба писати `<string>` явно.
- [Total TypeScript — Matt Pocock](https://www.totaltypescript.com/books/total-typescript-essentials)
  Безкоштовна книга-практикум від визнаного експерта. Use for: інтерактивні вправи на generics і type-level код.
- [type-challenges (GitHub)](https://github.com/type-challenges/type-challenges)
  Колекція задач на типи від easy до extreme. Use for: тренування навичок у бою після основ.
- [TS Playground](https://www.typescriptlang.org/play)
  Онлайн-редактор, що показує виведені типи при наведенні. Use for: миттєва перевірка «який тип вивів TS».

## Wisdom (Communities)

- [r/algorithms](https://reddit.com/r/algorithms)
  Обговорення алгоритмів і складності. Use for: перевірити своє розуміння, поставити «чому» питання.
- [Computer Science Stack Exchange](https://cs.stackexchange.com/)
  Високоякісні відповіді на теоретичні питання (інваріанти, докази). Use for: глибокі питання по аналізу.
- [LeetCode — Sorting tag](https://leetcode.com/tag/sorting/)
  Задачі, де quicksort/partition застосовується (Kth largest, Dutch national flag). Use for: перевірка навичок у бою.
- [r/typescript](https://reddit.com/r/typescript)
  Активна спільнота по TS, включно з питаннями по типах і generics. Use for: розбір складних сигнатур, «чому так не типізується».
- [TypeScript Community Discord](https://discord.com/invite/typescript)
  Канал #help з швидкими відповідями практиків. Use for: живі питання по type-level коду.

> Поки що спільноти запропоновані, але не обов'язкові — мета фундаментальна, не соціальна. Якщо не хочеш долучатись, скажи, і я приберу цей розділ.
