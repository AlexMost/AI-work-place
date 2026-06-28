# Resources

High-trust sources for understanding three.js, grounded to the pool-spy 3D race.

## Primary

- **three.js Manual — Fundamentals** · https://threejs.org/manual/en/fundamentals.html
  The canonical mental model: Scene / Camera / Renderer, Mesh = Geometry + Material,
  the scene-graph (Object3D parent→child) and the requestAnimationFrame render loop.
  Trust: official. Read this first; every lesson cites it.

- **three.js Manual — Scenegraph** · https://threejs.org/manual/en/scenegraph.html
  Why children inherit a parent's transform (the car-and-wheels example). This is the
  exact idea behind `Group` for the footballer body and the hip/shoulder pivots.

## Reference docs (API)

- **Group** · https://threejs.org/docs/#api/en/objects/Group — a container Object3D
- **Mesh** · https://threejs.org/docs/#api/en/objects/Mesh
- **CapsuleGeometry** · https://threejs.org/docs/#api/en/geometries/CapsuleGeometry — torso & limbs
- **SphereGeometry** · https://threejs.org/docs/#api/en/geometries/SphereGeometry — head & ball
- **MeshBasicMaterial** · https://threejs.org/docs/#api/en/materials/MeshBasicMaterial — flat colour, ignores lights (glow comes from bloom)

## The code being studied

- `footbal/.claude/skills/pool-spy/scripts/pool_spy.py`
  - `makeRunner()` ~ line 895 — builds one footballer
  - the render loop `tick = function(dt)` ~ line 960 — animates the run cycle
  - `init3D()` ~ line 757 — scene, camera, lights, field, bloom
