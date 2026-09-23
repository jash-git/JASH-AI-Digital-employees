# Placing Elements Along a Spline Path (Geometry Measurement)

When you need to position a shooter, spawn point, or UI element relative to a spline path
(e.g. Catmull-Rom in `canvas-game`), don't guess coordinates — **measure the path empirically**
and compute clearance + aim coverage from real data. This avoids overlaps and unreachable-aim bugs.

## Technique: sample the path, then compute geometry in Python

The game exposes a position-by-distance function (e.g. `posAt(d)`). Sample it densely to get the
actual curve, then do all placement math in Python where you have full control.

### 1. Dense-sample the path
```python
pts = await page.evaluate("""() => {
    const z = window.zuma;   // or whatever global exposes posAt
    const out = [];
    for (let d = 0; d <= TOTAL; d += 2) {
        const a = z.posAt(d);
        out.push({ x: +a.x.toFixed(2), y: +a.y.toFixed(2) });
    }
    return out;
}""")
```

### 2. Clearance = min distance from candidate point to any path sample
```python
def min_dist(px, py):
    return min(math.hypot(pt["x"] - px, pt["y"] - py) for pt in pts)
```
The ribbon half-width is ~23px; the shooter radius ~34px. Require clearance **>= 38–45px** so the
element sits clear of the track without being pushed to a corner. Prefer points near the path
centroid / bounding-box center for a balanced look, then pick the one with the best clearance.

### 3. Aim coverage (for a shooter)
A bottom-placed shooter only needs an upper-arc aim clamp because balls sit above it. A **middle**
shooter has balls all around it → the clamp must widen to nearly a full circle or it can't hit
balls below it. Compute the required range empirically:

```python
# For every chain-ball position along the track, compute atan2 relative to shooter (Sx,Sy):
angs = [math.atan2(ball.y - Sy, ball.x - Sx) for each ball]
lo, hi = min(degs), max(degs)          # e.g. [-179.7, 179.5] -> ~359deg span
# Set clamp bounds just past +/-180 (e.g. -Math.PI-0.35 .. Math.PI+0.35) so every ball is reachable;
# only a tiny wedge straight behind the frog body is excluded.
```
Verify: for each sampled ball, recompute `atan2` then apply the clamp and confirm it moves <1.2°.

## Pitfalls learned this session
- **Shooter at bottom vs middle changes the aim model.** Bottom = upper-arc clamp works. Middle =
  balls surround it; you MUST widen the clamp (near-full-circle) or lower balls become unaimable.
  Recompute the clamp bounds from sampled ball positions rather than assuming a fixed arc.
- **Don't place on the midpoint of the curve blindly.** The true path midpoint can sit ON the ribbon
  (clearance ~0px). Use the centroid / bounding-box center, or offset perpendicular to the tangent,
  and verify clearance with min-distance-to-track before committing.
- **Initial chain placement matters visually.** Building the initial chain from `END_DIST` (skull end)
  leaves ~90% of the track empty — balls look bunched at the far end instead of starting near the
  feeder. Build it from `START_DIST` (feeder side) so it extends toward the skull.
