# Notes

## User profile
- Strong general programmer; near-zero 3D / three.js / WebGL.
- Wants to understand the *existing* pool-spy code, not build new scenes.
- Lessons in Ukrainian.

## Teaching approach for this workspace
- Every concept is introduced through the real `pool_spy.py` code, then generalised —
  never abstract toy demos first.
- Keep lessons tiny (one win each). Working memory is the bottleneck for a 3D beginner.
- Cite threejs.org on every claim.

## Planned lesson arc
1. ✅ Anatomy of a footballer — scene graph, Mesh = Geometry + Material, the body parts
2. The limb pivot trick — nested Group with an offset mesh so it rotates at hip/shoulder
3. The run cycle — sine wave in the render loop drives all the swinging
4. (optional) The supporting cast — ball, trail, camera framing, bloom glow
