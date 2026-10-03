---
name: motion-advanced
description: Advanced motion patterns for React / Next.js — drag & drop, gestures, text animations, SVG path drawing, custom hooks, imperative sequences (useAnimate), loaders, and the full API decision tree. Requires motion-foundations. Use when building drag and drop, gestures, text or SVG animation, or imperative animation sequences in React or Next.js.
tags: [motion, animation, advanced, gestures, svg]
category: frontend
author: jeff
metadata:
  version: 1.0.0
---

# Motion Advanced

Complex, interactive, and physics-based animation patterns.
Requires `motion-foundations` to be set up first.
Use these when `motion-patterns` is not enough.

## When to Activate

- Building drag-to-dismiss sheets, swipe gestures, or reorderable lists
- Animating text word-by-word, character-by-character, or as a live counter
- Drawing SVG paths, morphing icons, or animating circular progress
- Writing a custom animation hook (`useScrollReveal`, magnetic button, cursor follower)
- Sequencing multi-step animations imperatively with `useAnimate`
- Building spinners, shimmer skeletons, pulse indicators, or loading button states

## Outputs

This skill produces:

- Drag interactions: draggable cards, drag-to-dismiss sheets, `Reorder.Group` lists
- Gesture hooks: swipe detection, long press, pinch outline
- Text animation components: word reveal, character typewriter, number counter
- SVG animation: path draw-on, icon morph, stroke progress ring
- Custom hooks: `useScrollReveal`, `useHoverScale`, `useNavigationDirection`, `useInViewOnce`
- Imperative sequences via `useAnimate` with interrupt-safe `async/await`
- Loader components: spinner, shimmer, pulse dot, progress bar, button loading state

## Principles

- Physics-based motion (`useSpring`, `springs.*`) always feels more natural than duration-based for direct manipulation.
- `useMotionValue` + `useTransform` computes derived values without triggering re-renders.
- `useAnimate` sequences are imperative and interrupt-safe — calling `animate()` mid-flight cancels the previous animation automatically.
- Motion values (`useMotionValue`, `useSpring`) are SSR-safe and do not cause hydration errors.

## Rules

1. **Drag interactions must be tested on touch devices**, not just mouse. `drag` prop works on both but feel and threshold differ.
2. **Infinite animations must pause when `document.visibilityState === "hidden"`.** Background tabs must not consume GPU/CPU.
3. **Swipe threshold must be explicit.** Never infer intent from velocity alone; combine `offset` + `velocity` checks.
4. **`useAnimate` scope ref must be attached to a mounted DOM element.** Calling `animate()` before mount throws silently.
5. **Motion values must not be recreated on render.** `useMotionValue(0)` inside a component body is correct; `new MotionValue(0)` in a render is not.
6. **All token values are imported from `motion-foundations`.** No inline numbers.
7. **Custom hooks must handle cleanup.** Every `window.addEventListener` needs a matching `removeEventListener` in the `useEffect` return.
8. **SVG morphing requires equal path command counts.** Paths with different command structures snap instead of interpolating.

## Decision Guidance

### Choosing the right advanced API

| Scenario | API |
| ------------------------------ | -------------------------------- |
| Drag with physics on release | `drag` + `dragTransition: springs.release` |
| Ordered drag-to-reorder list | `Reorder.Group` + `Reorder.Item` |
| Dismiss on drag offset | `drag="y"` + `onDragEnd` offset check |
| Swipe left/right | `drag="x"` + `onDragEnd` offset check |
| Long press | `useLongPress` hook |
| Value smoothed over time | `useSpring` |
| Value derived from another | `useTransform` |
| Multi-step sequence | `useAnimate` with `async/await` |
| One-shot imperative animation | `animate()` from `motion` |
| Text entering word by word | Stagger on `inline-block` spans |
| SVG drawing on | `pathLength` 0 → 1 |
| SVG morph | `d` attribute tween (equal commands) |
| Circular progress | `strokeDashoffset` tween |

### When to use `useSpring` vs a spring transition

| | `useSpring` | `transition: springs.*` |
| -------------- | ---------------------------------------- | ----------------------- |
| Use for | Cursor follower, pointer-tracked values | Discrete state changes |
| Updates | Continuous, on every frame | Triggered by state change |
| Interrupt | Smooth — physics picks up from velocity | Restarts from current value |

## Core Concepts

### useMotionValue + useTransform

Reactive computation without re-renders:

```tsx
const x = useMotionValue(0)
const opacity = useTransform(x, [-200, 0, 200], [0, 1, 0])
// opacity updates every frame as x changes — no setState, no re-render
```

### useAnimate

Returns `[scope, animate]`. The scope ref must be attached to a DOM element.
`animate()` calls are interrupt-safe — calling mid-flight cancels the previous run.

```tsx
const [scope, animate] = useAnimate()

async function play() {
  await animate(".step-1", { opacity: 1 }, { duration: 0.3 })
  await animate(".step-2", { x: 0 },       { duration: 0.4 })
        animate(".step-3", { scale: 1 },    { duration: 0.25 })  // fire and forget
}

return <div ref={scope}>...</div>
```

## Code Examples

### Draggable card

```tsx
"use client"
import { motion } from "motion/react"
import { springs, motionTokens } from "@/lib/motion-tokens"

<motion.div
  drag
  dragConstraints={{ left: -100, right: 100, top: -100, bottom: 100 }}
  dragElastic={0.1}
  whileDrag={{
    scale: motionTokens.scale.pop,
    boxShadow: "0 16px 40px rgba(0,0,0,0.2)",
  }}
  dragTransition={springs.release}
/>
```

See [references/gesture-examples.md](references/gesture-examples.md) for drag-to-dismiss sheets, reorderable lists, swipe detection and long press.

See [references/text-svg-ui-examples.md](references/text-svg-ui-examples.md) for word reveals, counters, SVG draw-on, progress rings, scroll reveal, cursor follower, skeletons, loading buttons and visibility-paused loops.

## End-to-End Example

See [references/end-to-end-example.md](references/end-to-end-example.md) for a full worked example combining the advanced motion APIs.

## Constraints / Non-Goals

This skill does **not** cover:

- Token and spring definitions → see `motion-foundations`
- Standard UI patterns (button, modal, stagger, page transitions) → see `motion-patterns`
- CSS-only animations or Tailwind `animate-*` without `motion/react`
- Canvas or WebGL-based animation (Three.js, Pixi, etc.)
- Full drag-and-drop systems with external state managers (dnd-kit, react-beautiful-dnd)
- Game-loop or frame-by-frame animation

## Anti-Patterns

| Anti-pattern | Rule violated | Fix |
| ---------------------------------------------- | ------- | ------------------------------------------------ |
| `drag` tested only on desktop | Rule 1 | Test on touch emulator and real device |
| `animate={{ repeat: Infinity }}` with no pause | Rule 2 | Add `visibilitychange` listener |
| `onDragEnd` checking only offset, not velocity | Rule 3 | Check both `info.offset` and `info.velocity` |
| `animate(scope, ...)` before `useEffect` | Rule 4 | Call `animate()` only after mount |
| `const x = new MotionValue(0)` in render | Rule 5 | Use `const x = useMotionValue(0)` |
| `transition={{ duration: 1.2 }}` inline | Rule 6 | Use `motionTokens.duration.crawl` |
| `useEffect` without cleanup | Rule 7 | Return `removeEventListener` / `controls.stop` |
| SVG morph between paths with different commands | Rule 8 | Normalize path commands before animating |

## Related Skills

- **`motion-foundations`** — defines all tokens, springs, `useSafeMotion`, and SSR guards imported here. Must be set up before using this skill.
- **`motion-patterns`** — handles standard UI patterns (button, modal, stagger, page transitions, scroll reveals). Use it before reaching for the advanced patterns here.
- References: [gesture-examples](references/gesture-examples.md), [text-svg-ui-examples](references/text-svg-ui-examples.md), [end-to-end-example](references/end-to-end-example.md)
