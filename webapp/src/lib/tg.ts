import { retrieveLaunchParams, init as initSdk } from "@telegram-apps/sdk-react"

type TelegramWebApp = {
  openLink?: (url: string, options?: { try_instant_view?: boolean }) => void
}

declare global {
  interface Window {
    Telegram?: { WebApp?: TelegramWebApp }
  }
}

export function bootstrapTelegram() {
  initSdk()
}

export function getInitDataRaw(): string {
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
