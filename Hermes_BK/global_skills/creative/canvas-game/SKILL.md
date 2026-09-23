---
name: canvas-game
description: Build complete browser games using vanilla HTML5 Canvas + CSS + JavaScript with zero external dependencies. Covers game loops, path systems, collision detection, particle effects, Web Audio, and scoring.
---

# Canvas Game Development

Build complete browser games using vanilla HTML5 Canvas + CSS + JavaScript with zero dependencies.

## When to use
- User asks for a browser game with no external libraries
- "Pure HTML/CSS/JS game", "no dependencies", "single file game"
- Canvas-based interactive visualizations that need game mechanics

## Architecture Pattern

### 1. Single-file structure
All code in one `.html` file:
```html
<!DOCTYPE html>
<html>
<head><style>/* CSS */</style></head>
<body>
<canvas id="gameCanvas" width="W" height="H"></canvas>
<script>/* JS */</script>
</body>
</html>
```

### 2. Game loop
```javascript
let lastTime = 0;
function gameLoop(timestamp) {
    update();   // game logic
    render();   // drawing
    lastTime = timestamp;
    requestAnimationFrame(gameLoop);
}
requestAnimationFrame(gameLoop);
```

### 3. Path system (for orbiting/moving chains)
Use **Catmull-Rom splines** for smooth curves through waypoints:
```javascript
function catmullRom(p0, p1, p2, p3, t) {
    const t2 = t*t, t3 = t2*t;
    return {
        x: 0.5*((2*p1.x)+(-p0.x+p2.x)*t+(2*p0.x-5*p1.x+4*p2.x-p3.x)*t2+(-p0.x+3*p1.x-3*p2.x+p3.x)*t3),
        y: 0.5*((2*p1.y)+(-p0.y+p2.y)*t+(2*p0.y-5*p1.y+4*p2.y-p3.y)*t2+(-p0.y+3*p1.y-3*p2.y+p3.y)*t3),
    };
}
```
Pre-compute cumulative distances along the path for O(1) position lookup by distance.

### 4. Collision detection
- **Ball vs ball**: distance between centers < 2*radius
- **Projectile vs target**: find closest entity, check distance threshold
- Use a spatial index (grid or sorted list) for large numbers of entities

### 5. Matching logic (for match-3 style games)
1. Find consecutive same-type entities along the path/array
2. Expand outward from insertion point in both directions
3. If count >= 3, remove and close the gap
4. Recursively check for chain reactions

### 6. Particle system
```javascript
particles = [];
// Spawn
particles.push({ x, y, vx, vy, life, decay, radius, color });
// Update
p.x += p.vx; p.y += p.vy;
p.vx *= 0.97; p.vy *= 0.97;
p.life -= p.decay;
// Remove when life <= 0
```

### 7. Web Audio API (sound effects)
```javascript
function playSound(freq, duration, type='sine', vol=0.15) {
    const osc = audioCtx.createOscillator();
    const gain = audioCtx.createGain();
    osc.type = type; osc.frequency.value = freq;
    gain.gain.setValueAtTime(vol, audioCtx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + duration);
    osc.connect(gain); gain.connect(audioCtx.destination);
    osc.start(); osc.stop(audioCtx.currentTime + duration);
}
```

### 8. Combo/scoring system
Track consecutive matches with a frame counter. Bonus score multiplies with combo count.

## Pitfalls
- **Frog ball positioning**: the ball held by the shooter must be positioned relative to the shooter's angle, not screen coordinates
- **Path distance gaps**: when inserting/removing balls, adjust all subsequent ball distances to maintain proper spacing
- **AudioContext**: must be created/resumed after a user gesture (click/tap) — browsers block autoplay
- **Canvas scaling**: always account for `getBoundingClientRect()` ratio when mapping mouse coords to canvas space
- **requestAnimationFrame**: store `lastTime` for delta-time calculations if you need frame-rate independent movement

## Reference: Zuma Implementation
See `references/zuma-implementation.md` for the full Zuma game code and detailed architecture notes.
