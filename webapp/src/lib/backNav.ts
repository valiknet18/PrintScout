import { useEffect } from "react"
import { useLocation, useNavigate } from "react-router-dom"

const EDGE_PX = 30 // touch must start within this many px of the left edge
const MIN_DX = 80 // and travel at least this far right
const MAX_DY = 60 // with little vertical drift
const MAX_TIME_MS = 600

/**
 * Wires two back-navigation affordances:
 *   - left-edge swipe to go back (iOS-native gesture, missing from TG WebView)
 *   - Telegram's built-in BackButton (chevron in top bar on supported clients)
 *
 * Both are no-ops on the root route. Idempotent — safe to mount once at App.
 */
export function useBackNav() {
  const navigate = useNavigate()
  const location = useLocation()
  const isRoot = location.pathname === "/"

  // ─── Telegram BackButton ─────────────────────────────────────────────────
  useEffect(() => {
    const bb = window.Telegram?.WebApp?.BackButton
    if (!bb) return

    const onClick = () => navigate(-1)
    if (isRoot) {
      bb.hide?.()
    } else {
      bb.show?.()
      bb.onClick?.(onClick)
    }
    return () => {
      bb.offClick?.(onClick)
    }
  }, [isRoot, navigate])

  // ─── Edge-swipe gesture ──────────────────────────────────────────────────
  useEffect(() => {
    if (isRoot) return

    let startX = 0
    let startY = 0
    let startT = 0
    let active = false

    const onStart = (e: TouchEvent) => {
      const t = e.touches[0]
      if (!t) return
      // Only start tracking if the touch began at the left edge — leaves
      // horizontal scrollers (printer chip rows, etc.) untouched.
      if (t.clientX > EDGE_PX) {
        active = false
        return
      }
      startX = t.clientX
      startY = t.clientY
      startT = performance.now()
      active = true
    }

    const onEnd = (e: TouchEvent) => {
      if (!active) return
      active = false
      const t = e.changedTouches[0]
      if (!t) return
      const dx = t.clientX - startX
      const dy = Math.abs(t.clientY - startY)
      const dt = performance.now() - startT
      if (dx >= MIN_DX && dy <= MAX_DY && dt <= MAX_TIME_MS) {
        navigate(-1)
      }
    }

    window.addEventListener("touchstart", onStart, { passive: true })
    window.addEventListener("touchend", onEnd, { passive: true })
    return () => {
      window.removeEventListener("touchstart", onStart)
      window.removeEventListener("touchend", onEnd)
    }
  }, [isRoot, navigate])
}
