import { useEffect, useMemo, useRef, useState } from "react"
import { useNavigate, useSearchParams } from "react-router-dom"
import { useInfiniteQuery, useQueries, useQuery } from "@tanstack/react-query"
import { ArrowLeft, Loader2, Search as SearchIcon } from "lucide-react"

import { ModelCard } from "@/components/ModelCard"
import {
  FitApi,
  PrintersApi,
  SearchApi,
  type FitResponse,
  type PaidFilter,
  type SearchHit,
} from "@/lib/api"
import { recentSearches } from "@/lib/recentSearches"

const PAID_OPTIONS: { value: PaidFilter; label: string }[] = [
  { value: "free", label: "Free" },
  { value: "paid", label: "Paid" },
  { value: "all", label: "All" },
]

export default function Search() {
  const navigate = useNavigate()
  const [params, setParams] = useSearchParams()

  const q = params.get("q") ?? ""
  const paid = (params.get("paid") as PaidFilter | null) ?? "free"
  const printerIdParam = params.get("printer_id")
  const printerId = printerIdParam ? Number(printerIdParam) : null
  const hideTooBig = params.get("hide_too_big") === "1"
  const inputRef = useRef<HTMLInputElement>(null)
  const [typed, setTyped] = useState(q)

  const { data: printers } = useQuery({
    queryKey: ["printers"],
    queryFn: PrintersApi.list,
  })

  // Auto-pick the only printer.
  useEffect(() => {
    if (!printerId && printers && printers.length === 1) {
      const next = new URLSearchParams(params)
      next.set("printer_id", String(printers[0].id))
      setParams(next, { replace: true })
    }
  }, [printerId, printers, params, setParams])

  // Autofocus input on first mount when no query yet.
  useEffect(() => {
    if (!q) inputRef.current?.focus()
  }, [q])

  // Sync local input when URL q changes externally (back/forward).
  useEffect(() => {
    setTyped(q)
  }, [q])

  const update = (patch: Record<string, string | null>) => {
    const next = new URLSearchParams(params)
    for (const [k, v] of Object.entries(patch)) {
      if (v == null || v === "") next.delete(k)
      else next.set(k, v)
    }
    setParams(next, { replace: true })
  }

  // Debounce typed → URL q (300ms). Skips no-op + handles cleanup.
  useEffect(() => {
    if (typed === q) return
    const id = window.setTimeout(() => update({ q: typed }), 300)
    return () => window.clearTimeout(id)
    // `params` is referenced inside `update` via closure; we intentionally
    // re-run only when `typed` or `q` changes, not on every params mutation.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [typed, q])

  const enabled = Boolean(printerId && q.trim().length > 0)
  const search = useInfiniteQuery({
    enabled,
    queryKey: ["search", { printerId, q, paid }],
    initialPageParam: 1,
    queryFn: ({ pageParam }) =>
      SearchApi.search({
        printerId: printerId!,
        q,
        paid,
        page: pageParam,
        pageSize: 30,
      }),
    getNextPageParam: (last, all) => {
      const loaded = all.reduce((sum, p) => sum + p.items.length, 0)
      return loaded < last.total ? all.length + 1 : undefined
    },
  })

  const items = useMemo(
    () => search.data?.pages.flatMap((p) => p.items) ?? [],
    [search.data],
  )
  const total = search.data?.pages[0]?.total ?? 0
  const firstPage = search.data?.pages[0]
  const translatedQuery =
    firstPage?.original_query && firstPage.query
      ? { original: firstPage.original_query, used: firstPage.query }
      : null

  // Persist successful searches into recents (after data lands for current q).
  useEffect(() => {
    if (search.isSuccess && q.trim()) recentSearches.add(q)
  }, [search.isSuccess, q])

  // Mirror per-card fit queries here so we can filter by status. TanStack
  // dedupes on queryKey, so the cards' own useQuery shares this cache.
  const fits = useQueries({
    queries: items.map((hit) => ({
      enabled: printerId != null,
      queryKey: ["fit", printerId, hit.source, hit.source_id],
      queryFn: () =>
        FitApi.check({
          printerId: printerId!,
          source: hit.source,
          sourceId: hit.source_id,
        }),
      staleTime: Infinity,
      retry: false,
    })),
  })

  const fitByKey = useMemo(() => {
    const map = new Map<string, FitResponse>()
    items.forEach((hit, i) => {
      const data = fits[i]?.data
      if (data) map.set(`${hit.source}:${hit.source_id}`, data)
    })
    return map
  }, [items, fits])

  const visibleItems = useMemo<SearchHit[]>(() => {
    if (!hideTooBig) return items
    return items.filter((hit) => {
      const fit = fitByKey.get(`${hit.source}:${hit.source_id}`)
      return fit?.status !== "too_big"
    })
  }, [items, fitByKey, hideTooBig])

  const fitsCount = useMemo(
    () =>
      items.filter(
        (hit) =>
          fitByKey.get(`${hit.source}:${hit.source_id}`)?.status === "fits",
      ).length,
    [items, fitByKey],
  )

  return (
    <div className="flex min-h-full flex-col">
      <header className="sticky top-0 z-10 flex items-center gap-2 bg-tg-bg px-3 pt-3 pb-2">
        <button
          type="button"
          onClick={() => navigate(-1)}
          aria-label="Back"
          className="rounded-full p-2 active:bg-tg-secondary-bg"
        >
          <ArrowLeft className="size-5" />
        </button>
        <div className="flex flex-1 items-center gap-2 rounded-2xl bg-tg-secondary-bg px-3">
          <SearchIcon className="size-4 text-tg-hint" />
          <input
            ref={inputRef}
            value={typed}
            onChange={(e) => setTyped(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                e.preventDefault()
                update({ q: typed })
                inputRef.current?.blur()
              }
            }}
            placeholder="Search models..."
            className="h-11 w-full bg-transparent outline-none placeholder:text-tg-hint"
            autoComplete="off"
            enterKeyHint="search"
          />
        </div>
      </header>

      <PrinterPicker
        printers={printers}
        printerId={printerId}
        onChange={(id) => update({ printer_id: String(id) })}
      />

      <div className="flex flex-wrap items-center gap-2 px-3 pb-3 pt-1">
        <div className="inline-flex rounded-full bg-tg-secondary-bg p-1">
          {PAID_OPTIONS.map((o) => (
            <button
              key={o.value}
              type="button"
              onClick={() => update({ paid: o.value })}
              className={`rounded-full px-4 py-1.5 text-sm transition-colors ${
                paid === o.value
                  ? "bg-tg-button text-tg-button-text"
                  : "text-tg-hint"
              }`}
            >
              {o.label}
            </button>
          ))}
        </div>
        <button
          type="button"
          onClick={() => update({ hide_too_big: hideTooBig ? null : "1" })}
          className={`rounded-full px-4 py-1.5 text-sm transition-colors ${
            hideTooBig
              ? "bg-tg-button text-tg-button-text"
              : "bg-tg-secondary-bg text-tg-hint"
          }`}
        >
          Fits only
        </button>
      </div>

      <main className="px-3 pb-6">
        {!printerId ? (
          <Hint text="Pick a printer to start searching." />
        ) : !enabled ? (
          <Hint text="Type something above to search." />
        ) : search.isLoading ? (
          <CenterSpinner />
        ) : search.isError ? (
          <Hint text={`Search failed: ${(search.error as Error).message}`} />
        ) : items.length === 0 ? (
          <Hint text="No models match. Try a broader query or relax the filter." />
        ) : (
          <>
            {translatedQuery && (
              <div className="mb-3 rounded-xl bg-tg-secondary-bg px-3 py-2 text-xs text-tg-hint">
                Showing results for{" "}
                <span className="font-medium text-tg-text">
                  "{translatedQuery.used}"
                </span>{" "}
                — translated from "{translatedQuery.original}"
              </div>
            )}
            <p className="mb-2 text-xs text-tg-hint">
              {hideTooBig
                ? `${visibleItems.length} fitting · ${fitsCount}/${items.length} checked`
                : `${total.toLocaleString()} results`}
            </p>
            {visibleItems.length === 0 ? (
              <Hint text="No models in this batch fit. Load more or relax the toggle." />
            ) : (
              <ul className="grid grid-cols-2 gap-3">
                {visibleItems.map((hit) => (
                  <li key={`${hit.source}:${hit.source_id}`}>
                    <ModelCard hit={hit} printerId={printerId} />
                  </li>
                ))}
              </ul>
            )}
            {search.hasNextPage && (
              <button
                type="button"
                onClick={() => search.fetchNextPage()}
                disabled={search.isFetchingNextPage}
                className="mt-4 flex w-full items-center justify-center gap-2 rounded-xl bg-tg-secondary-bg py-3 text-sm font-medium disabled:opacity-50"
              >
                {search.isFetchingNextPage ? (
                  <>
                    <Loader2 className="size-4 animate-spin" /> Loading...
                  </>
                ) : (
                  "Load more"
                )}
              </button>
            )}
          </>
        )}
      </main>
    </div>
  )
}

function PrinterPicker({
  printers,
  printerId,
  onChange,
}: {
  printers: { id: number; name: string }[] | undefined
  printerId: number | null
  onChange: (id: number) => void
}) {
  if (!printers || printers.length <= 1) return null
  return (
    <ul className="flex gap-2 overflow-x-auto px-3 py-2">
      {printers.map((p) => (
        <li key={p.id} className="shrink-0">
          <button
            type="button"
            onClick={() => onChange(p.id)}
            className={`rounded-full px-3 py-1.5 text-sm transition-colors ${
              p.id === printerId
                ? "bg-tg-button text-tg-button-text"
                : "bg-tg-secondary-bg text-tg-hint"
            }`}
          >
            {p.name}
          </button>
        </li>
      ))}
    </ul>
  )
}

function Hint({ text }: { text: string }) {
  return <p className="mt-12 text-center text-sm text-tg-hint">{text}</p>
}

function CenterSpinner() {
  return (
    <div className="mt-12 flex justify-center">
      <Loader2 className="size-6 animate-spin text-tg-hint" />
    </div>
  )
}
