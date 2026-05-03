const KEY = "printscout:recent_searches"
const CAP = 8

function safeRead(): string[] {
  try {
    const raw = window.localStorage.getItem(KEY)
    if (!raw) return []
    const parsed = JSON.parse(raw)
    return Array.isArray(parsed) ? parsed.filter((x) => typeof x === "string") : []
  } catch {
    return []
  }
}

function safeWrite(values: string[]) {
  try {
    window.localStorage.setItem(KEY, JSON.stringify(values))
  } catch {
    // private mode / quota exceeded — silent
  }
}

export const recentSearches = {
  list(): string[] {
    return safeRead()
  },
  add(q: string) {
    const trimmed = q.trim()
    if (!trimmed) return
    const lower = trimmed.toLowerCase()
    const without = safeRead().filter((x) => x.toLowerCase() !== lower)
    safeWrite([trimmed, ...without].slice(0, CAP))
  },
  remove(q: string) {
    const lower = q.trim().toLowerCase()
    safeWrite(safeRead().filter((x) => x.toLowerCase() !== lower))
  },
  clear() {
    safeWrite([])
  },
}
