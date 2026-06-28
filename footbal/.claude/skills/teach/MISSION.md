# Mission: How pool-spy generates its 3D footballers (three.js)

## Why
The user runs the `pool-spy` skill, which renders a dark-neon 3D race of pool members
as glowing running footballers (`standings.html`, built by `pool_spy.py`). They want to
genuinely understand how that 3D scene is generated — to be able to read the three.js
code in `makeRunner` / the render loop and know exactly what each piece does and why.
This is understanding-driven curiosity, not a plan to build their own 3D apps (yet).

## Success looks like
- Can read `makeRunner()` (pool_spy.py:895) line by line and explain what appears on screen
- Can explain the core three.js model: Scene graph, Mesh = Geometry + Material, Group hierarchy
- Can explain how the limbs swing (the pivot trick + the sine-wave run cycle in the render loop)
- Can point to the ball, trail, camera and bloom and say what each does at a high level

## Constraints
- Near-zero prior 3D / three.js / WebGL knowledge — but a strong general programmer
- Learning preference: understand the *existing* code, grounded in the real file, not toy demos
- Ukrainian-language lessons

## Out of scope (for now)
- Writing new three.js scenes from scratch
- Shaders / GLSL, advanced lighting, performance tuning
- The data pipeline (API fetch, build_timeline) — focus is the rendering, not the data
