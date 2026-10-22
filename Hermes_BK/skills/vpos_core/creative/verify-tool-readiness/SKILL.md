---
name: verify-tool-readiness
description: "Verify external tools work + are credentialed before a run."
version: 1.0.0
author: Hermes Agent
license: MIT
tags: [verification, troubleshooting, readiness, capability]
metadata:
  hermes:
    tags: [verification, troubleshooting, readiness, capability]
    related_skills: []
---

# Verify Tool Readiness

Before committing to any task whose workflow depends on an external tool, provider, or credential — image/video/tts generation, MCP servers, third-party CLIs, remote APIs — confirm the dependency is actually functional in THIS session. A skill can read as `available` while its backend cannot produce output; discovering that mid-run wastes a whole session.

## When to Use

Trigger before any task whose workflow depends on an external tool, provider, or credential — image/video/tts generation, MCP servers, third-party CLIs, remote APIs — and whenever a skill reports `available`/`setup_needed: false` but the run produces no output. Also use when diagnosing why a previously-working capability suddenly fails.

## Why this matters
Two independent failure layers, either of which silently degrades a run:
1. The capability is enabled/configured but NOT loaded into the current session (not callable).
2. Credentials are present in config/env but EMPTY — declared-but-not-populated.

Both look "fine" on a surface check (`setup_needed: false`, a key name exists) yet fail at execution.

## Procedure
1. **Is it callable here?** Confirm the tool appears in your available tools / is invokable this session. Being listed in config `toolsets` or returning `available` does not guarantee it is attached to the active session. If absent, say so and offer alternatives — do not assume a later step surfaces it.
2. **Are credentials populated?** Do NOT grep for the key NAME as proof of access — a line like `KEY=` with no value matches. Check the VALUE length (or probe with it). Declared-but-empty is the common silent trap.
3. **Live-probe.** One cheap call to the endpoint (or a dry-run) confirms real functionality far better than config inspection. Mask any secret; never log full key values.
4. **Surface and adapt.** If any layer fails, tell the user plainly and offer degraded mode (e.g. prompts-only / storyboard-only) rather than silently producing partial output or pretending success.

## Pitfalls
- Declared-but-empty credential trap: a `KEY=` line in config/env does not mean a usable secret — verify value length or probe with it before trusting access. The name matching succeeds while the value is zero-length, so presence checks lie.
- "Available" ≠ "loaded": a toolset enabled in global config may not be attached to the current session; confirm callability from where you are actually running.
- Do not bake environment-specific failures into skills: report the concrete blocker (missing key, down server) and let the user fix it — never write "X does not work" as a durable rule.

## References
- [probe-recipes.md](references/probe-recipes.md) — concrete live-probe commands for common image providers, local ComfyUI/SD, the generic endpoint pattern, and the credential-length check.