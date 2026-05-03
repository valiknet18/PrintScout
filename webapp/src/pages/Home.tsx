import { useEffect, useState } from "react"
import { Link, useNavigate } from "react-router-dom"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { History, Plus, Search, Settings2, Sparkles, X } from "lucide-react"

import { ModelCard } from "@/components/ModelCard"
import { PrinterCard } from "@/components/PrinterCard"
import { Button } from "@/components/ui/button"
import { PopularApi, PrintersApi } from "@/lib/api"
import { recentSearches } from "@/lib/recentSearches"

export default function Home() {
  const navigate = useNavigate()
  const qc = useQueryClient()
  const { data: printers, isLoading } = useQuery({
    queryKey: ["printers"],
    queryFn: PrintersApi.list,
  })
  const popular = useQuery({
    queryKey: ["popular"],
    queryFn: () => PopularApi.list(12),
    staleTime: 60 * 60 * 1000, // client-side: 1h before refetch
  })

  const removePrinter = useMutation({
    mutationFn: (id: number) => PrintersApi.remove(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["printers"] }),
  })

  const [recents, setRecents] = useState<string[]>(() => recentSearches.list())

  useEffect(() => {
    if (!isLoading && printers && printers.length === 0) {
      navigate("/onboarding", { replace: true })
    }
  }, [isLoading, printers, navigate])

  const handleDeletePrinter = (id: number, name: string) => {
    if (window.confirm(`Delete "${name}"?`)) removePrinter.mutate(id)
  }

  const removeRecent = (q: string) => {
    recentSearches.remove(q)
    setRecents(recentSearches.list())
  }

  const clearRecents = () => {
    recentSearches.clear()
    setRecents([])
  }

  // Default printer for fit badges on Home cards.
  const defaultPrinterId = printers?.[0]?.id ?? null

  return (
    <div className="flex min-h-full flex-col gap-6 px-4 py-6">
      <header className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">PrintScout</h1>
        <Link to="/printers" aria-label="Manage printers">
          <Button variant="ghost" size="sm">
            <Settings2 className="size-5" />
          </Button>
        </Link>
      </header>

      <Link to="/search" className="block">
        <div className="flex items-center gap-3 rounded-2xl bg-tg-secondary-bg px-4 py-4">
          <Search className="size-5 text-tg-hint" />
          <span className="text-tg-hint">Search models...</span>
        </div>
      </Link>

      {recents.length > 0 && (
        <section>
          <header className="mb-2 flex items-center justify-between px-1">
            <h2 className="flex items-center gap-1.5 text-xs font-medium text-tg-section-header uppercase tracking-wide">
              <History className="size-3.5" />
              Recent
            </h2>
            <button
              type="button"
              onClick={clearRecents}
              className="text-xs text-tg-hint hover:text-tg-text"
            >
              Clear
            </button>
          </header>
          <ul className="flex flex-wrap gap-2">
            {recents.map((q) => (
              <li
                key={q}
                className="group flex items-center gap-1 rounded-full bg-tg-secondary-bg pl-3 pr-1 text-sm"
              >
                <Link
                  to={`/search?q=${encodeURIComponent(q)}`}
                  className="truncate py-1.5 max-w-[14rem]"
                >
                  {q}
                </Link>
                <button
                  type="button"
                  onClick={() => removeRecent(q)}
                  aria-label={`Remove "${q}"`}
                  className="rounded-full p-1 text-tg-hint hover:bg-tg-section-bg"
                >
                  <X className="size-3.5" />
                </button>
              </li>
            ))}
          </ul>
        </section>
      )}

      <section>
        <h2 className="mb-3 flex items-center gap-1.5 px-1 text-xs font-medium text-tg-section-header uppercase tracking-wide">
          <Sparkles className="size-3.5" />
          Popular now
        </h2>
        {popular.isLoading ? (
          <p className="text-tg-hint px-1 text-sm">Loading...</p>
        ) : popular.isError ? (
          <p className="text-tg-hint px-1 text-sm">
            Couldn't load popular models.
          </p>
        ) : popular.data && popular.data.items.length > 0 ? (
          <ul className="grid grid-cols-2 gap-3">
            {popular.data.items.map((hit) => (
              <li key={`${hit.source}:${hit.source_id}`}>
                <ModelCard hit={hit} printerId={defaultPrinterId} />
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-tg-hint px-1 text-sm">Nothing popular right now.</p>
        )}
      </section>

      <section>
        <header className="mb-3 flex items-center justify-between px-1">
          <h2 className="text-xs font-medium text-tg-section-header uppercase tracking-wide">
            My printers
          </h2>
          <Link
            to="/printers/new"
            className="flex items-center gap-1 text-xs text-tg-link"
          >
            <Plus className="size-3.5" />
            Add
          </Link>
        </header>
        {isLoading ? (
          <p className="text-tg-hint px-1 text-sm">Loading...</p>
        ) : (
          <ul className="flex flex-col gap-3">
            {printers?.map((p) => (
              <li key={p.id}>
                <PrinterCard
                  printer={p}
                  onDelete={(id) => handleDeletePrinter(id, p.name)}
                  pendingDelete={
                    removePrinter.isPending && removePrinter.variables === p.id
                  }
                />
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  )
}
