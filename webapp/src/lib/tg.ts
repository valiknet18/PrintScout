import { retrieveLaunchParams, init as initSdk } from "@telegram-apps/sdk-react"

type TelegramBackButton = {
  show?: () => void
  hide?: () => void
  onClick?: (cb: () => void) => void
  offClick?: (cb: () => void) => void
}

type TelegramWebApp = {
  initData?: string
  openLink?: (url: string, options?: { try_instant_view?: boolean }) => void
  ready?: () => void
  expand?: () => void
  BackButton?: TelegramBackButton
}

declare global {
  interface Window {
    Telegram?: { WebApp?: TelegramWebApp }
  }
}

export function bootstrapTelegram() {
  // Officially-injected JS API: ensure WebApp is marked ready (some Telegram
  // clients won't populate initData until ready() is called).
  const tg = window.Telegram?.WebApp
  tg?.ready?.()
  tg?.expand?.()

  try {
    initSdk()
  } catch {
    // SDK init can throw outside a real Telegram context — that's fine.
  }
}

export function getInitDataRaw(): string {
  // 1) Prefer the canonical Telegram-injected global. It's the most reliable
  //    source and is always populated when launched as a real WebApp.
  const fromTelegram = window.Telegram?.WebApp?.initData
  if (typeof fromTelegram === "string" && fromTelegram.length > 0) {
    return fromTelegram
  }
  // 2) Fall back to the SDK's launch-params parser (handles cases where the
  //    Telegram script hasn't loaded but launch params are still in the URL).
  try {
    const lp = retrieveLaunchParams(true)
    return typeof lp.initDataRaw === "string" ? lp.initDataRaw : ""
  } catch {
    return ""
  }
}

export function openExternalLink(url: string) {
  const tg = window.Telegram?.WebApp
  if (tg?.openLink) {
    tg.openLink(url, { try_instant_view: false })
  } else {
    window.open(url, "_blank", "noopener,noreferrer")
  }
}
