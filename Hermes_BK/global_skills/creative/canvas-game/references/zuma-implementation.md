# Zuma Game Implementation (Session 2026-08-11)

## Key Design Decisions

### Path Generation
- Catmull-Rom spline through 15 waypoints for smooth organic curve
- 60 segments per waypoint pair = ~840 total path points
- Pre-compute cumulative distances for O(log n) position lookup via binary search

### Ball Chain Mechanics
- Balls placed at fixed intervals (BALL_SPACING = 30px) along path distance
- Insertion: find closest ball, insert at that distance, push subsequent balls forward
- Removal: splice matched balls, pull remaining balls back by gap size
- Gap closure is critical — without it balls drift apart or overlap

### Collision System
- Projectile travels at PROJECTILE_SPEED = 12 px/frame
- Per-frame: check distance to all balls; if < BALL_RADIUS + 4, insert
- Binary search finds closest ball (no need to check all)

### Match Detection
- After insertion, expand outward from insertion index
- Count consecutive same-color balls
- Threshold: 3+ for match
- Combo: consecutive matches within 60 frames multiply score

### Rendering Pipeline
1. Background gradient + twinkling stars
2. Path (3-layer: glow, outer, inner)
3. Skull at path end (with danger glow when balls approach)
4. Balls (radial gradient + shine highlight + shadow)
5. Projectile with trail
6. Particles (gravity + friction)
7. Frog with eyes tracking mouse
8. Combo text + score popups

### Sound Design
- Shoot: 600Hz square wave, 100ms
- Hit: 300Hz triangle, 150ms
- Match: ascending arpeggio (400+Hz), one per matched ball
- Lose: descending sawtooth
- Win: ascending major chord (C-E-G-C)

## File
`/home/vblinux/02/zuma.html` — 1085 lines, fully self-contained
