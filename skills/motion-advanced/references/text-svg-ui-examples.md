# Advanced Motion Text, SVG and UI Examples

This file covers word reveals, counters, SVG draw-on, progress rings, scroll reveal, cursor follower, skeletons, loading buttons and visibility-paused loops.

### Word-by-word reveal

```tsx
"use client"
import { motion } from "motion/react"
import { springs } from "@/lib/motion-tokens"

export function AnimatedText({ text }: { text: string }) {
  return (
    <motion.p
      variants={{ visible: { transition: { staggerChildren: 0.05 } } }}
      initial="hidden"
      animate="visible"
    >
      {text.split(" ").map((word, i) => (
        <motion.span
          key={i}
          className="inline-block mr-1"
          variants={{
            hidden:  { opacity: 0, y: 12 },
            visible: { opacity: 1, y: 0, transition: springs.gentle },
          }}
        >
          {word}
        </motion.span>
      ))}
    </motion.p>
  )
}
```

### Number counter

```tsx
"use client"
import { useRef, useEffect } from "react"
import { animate } from "motion"
import { motionTokens } from "@/lib/motion-tokens"

export function Counter({ to }: { to: number }) {
  const nodeRef = useRef<HTMLSpanElement>(null)

  useEffect(() => {
    const controls = animate(0, to, {
      duration: motionTokens.duration.crawl,
      ease: motionTokens.easing.smooth,
      onUpdate: (v) => {
        if (nodeRef.current) nodeRef.current.textContent = Math.round(v).toString()
      },
    })
    return controls.stop   // Rule 7: cleanup
  }, [to])

  return <span ref={nodeRef} />
}
```

### SVG path draw-on

```tsx
"use client"
import { motion } from "motion/react"
import { motionTokens } from "@/lib/motion-tokens"

<motion.path
  d="M 0 100 Q 50 0 100 100"
  initial={{ pathLength: 0, opacity: 0 }}
  animate={{ pathLength: 1, opacity: 1 }}
  transition={{ duration: motionTokens.duration.slow, ease: motionTokens.easing.smooth }}
/>
```

### Stroke progress ring

```tsx
"use client"
import { motion } from "motion/react"
import { motionTokens } from "@/lib/motion-tokens"

const CIRCUMFERENCE = 2 * Math.PI * 40   // r=40

export function ProgressRing({ progress }: { progress: number }) {
  return (
    <svg width="100" height="100" viewBox="0 0 100 100">
      <circle cx="50" cy="50" r="40" fill="none" stroke="#e5e7eb" strokeWidth="8" />
      <motion.circle
        cx="50" cy="50" r="40"
        fill="none" stroke="#6366f1" strokeWidth="8"
        strokeLinecap="round"
        strokeDasharray={CIRCUMFERENCE}
        animate={{ strokeDashoffset: CIRCUMFERENCE - (progress / 100) * CIRCUMFERENCE }}
        transition={{ duration: motionTokens.duration.normal, ease: motionTokens.easing.smooth }}
        style={{ rotate: -90, transformOrigin: "center" }}
      />
    </svg>
  )
}
```

### useScrollReveal hook

```tsx
"use client"
import { useRef } from "react"
import { useScroll, useTransform } from "motion/react"
import { motionTokens } from "@/lib/motion-tokens"

export function useScrollReveal() {
  const ref = useRef(null)
  const { scrollYProgress } = useScroll({ target: ref, offset: ["start end", "end start"] })
  const opacity = useTransform(scrollYProgress, [0, 0.3], [0, 1])
  const y       = useTransform(scrollYProgress, [0, 0.3], [motionTokens.distance.lg, 0])
  return { ref, style: { opacity, y } }
}

// Usage
const { ref, style } = useScrollReveal()
<motion.section ref={ref} style={style} />
```

### Cursor follower

```tsx
"use client"
import { useEffect } from "react"
import { motion, useMotionValue, useSpring } from "motion/react"
import { springs } from "@/lib/motion-tokens"

export function CursorFollower() {
  const x = useMotionValue(-100)
  const y = useMotionValue(-100)
  const sx = useSpring(x, springs.gentle)
  const sy = useSpring(y, springs.gentle)

  useEffect(() => {
    const move = (e: MouseEvent) => { x.set(e.clientX); y.set(e.clientY) }
    window.addEventListener("mousemove", move)
    return () => window.removeEventListener("mousemove", move)   // Rule 7
  }, [])

  return (
    <motion.div
      className="fixed top-0 left-0 w-6 h-6 rounded-full bg-indigo-500
                 pointer-events-none -translate-x-1/2 -translate-y-1/2 z-50"
      style={{ x: sx, y: sy }}
    />
  )
}
```

### Shimmer skeleton

```tsx
"use client"
import { useEffect } from "react"
import { motion, useAnimation } from "motion/react"
import { motionTokens } from "@/lib/motion-tokens"

export function ShimmerSkeleton({ className = "" }: { className?: string }) {
  const controls = useAnimation()

  useEffect(() => {
    const play = () =>
      controls.start({
        x: ["-100%", "100%"],
        transition: {
          repeat: Infinity,
          duration: motionTokens.duration.crawl,
          ease: motionTokens.easing.linear,
        },
      })

    const handleVisibility = () => {
      if (document.visibilityState === "hidden") controls.stop()
      else void play()
    }

    void play()
    document.addEventListener("visibilitychange", handleVisibility)
    return () => {
      controls.stop()
      document.removeEventListener("visibilitychange", handleVisibility)
    }
  }, [controls])

  return (
    <div className={`relative overflow-hidden bg-gray-200 rounded ${className}`}>
      <motion.div
        className="absolute inset-0 bg-gradient-to-r from-transparent via-white/60 to-transparent"
        initial={{ x: "-100%" }}
        animate={controls}
      />
    </div>
  )
}
```

### Button loading state

```tsx
"use client"
import { motion, AnimatePresence } from "motion/react"
import { motionTokens, springs } from "@/lib/motion-tokens"

export function LoadingButton({
  loading,
  label,
  onClick,
}: {
  loading: boolean
  label: string
  onClick: () => void
}) {
  return (
    <motion.button
      onClick={onClick}
      animate={{ opacity: loading ? 0.7 : 1 }}
      whileTap={loading ? {} : { scale: motionTokens.scale.press }}
      transition={springs.snappy}
      disabled={loading}
    >
      <AnimatePresence mode="wait">
        {loading ? (
          <motion.span
            key="loading"
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            transition={{ duration: motionTokens.duration.fast }}
          >
            …
          </motion.span>
        ) : (
          <motion.span
            key="label"
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            transition={{ duration: motionTokens.duration.fast }}
          >
            {label}
          </motion.span>
        )}
      </AnimatePresence>
    </motion.button>
  )
}
```

### Infinite animation with visibility pause

```tsx
"use client"
import { useEffect } from "react"
import { motion, useAnimation } from "motion/react"
import { motionTokens } from "@/lib/motion-tokens"

export function PulseDot() {
  const controls = useAnimation()

  useEffect(() => {
    const pulse = () =>
      controls.start({
        scale: [1, 1.4, 1],
        opacity: [1, 0.6, 1],
        transition: { repeat: Infinity, duration: motionTokens.duration.crawl },
      })

    // Rule 2: pause when tab is hidden
    const handleVisibility = () => {
      if (document.visibilityState === "hidden") controls.stop()
      else void pulse()
    }

    void pulse()
    document.addEventListener("visibilitychange", handleVisibility)
    // Rule 7: stop controls and remove listeners on unmount.
    return () => {
      controls.stop()
      document.removeEventListener("visibilitychange", handleVisibility)
    }
  }, [controls])

  return <motion.span className="w-2 h-2 rounded-full bg-green-400" animate={controls} />
}
```
