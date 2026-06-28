# Starting point: strong programmer, near-zero 3D

Established at workspace creation. The user is a confident general programmer but has
**near-zero** three.js / WebGL / 3D-graphics background. Mission is *understanding-driven*:
read and fully grasp the existing `pool-spy` 3D race code (`makeRunner` + render loop),
**not** building new scenes (see [[MISSION.md]]).

Implications for teaching:
- Introduce every 3D concept through the real `pool_spy.py` code, then generalise — no
  abstract toy demos first. This matches the user's stated preference.
- Cannot assume any 3D vocabulary: coordinate axes (Y-up), "mesh", "scene graph",
  "render loop" all need first-principles intro. Glossary started in `reference/glossary.html`.
- Lessons in Ukrainian.

No understanding *demonstrated* yet — this records the floor, not a result. Lesson 1
(anatomy: Mesh = Geometry + Material, Group hierarchy) authored; await quiz/discussion
evidence before raising the ZPD toward the pivot trick (lesson 2) and the run cycle.
