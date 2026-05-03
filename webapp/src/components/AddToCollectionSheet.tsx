import { useEffect, useState } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { Check, Loader2, Plus, X } from "lucide-react"

import { Button } from "@/components/ui/button"
import { CollectionsApi } from "@/lib/api"

type Props = {
  source: string
  sourceId: string
  onClose: () => void
}

export function AddToCollectionSheet({ source, sourceId, onClose }: Props) {
  const qc = useQueryClient()
  const [newName, setNewName] = useState("")

  const collections = useQuery({
    queryKey: ["collections"],
    queryFn: CollectionsApi.list,
  })

  const membership = useQuery({
    queryKey: ["collection-membership", source, sourceId],
    queryFn: () => CollectionsApi.membership(source, sourceId),
  })

  const inSet = new Set(membership.data ?? [])

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ["collections"] })
    qc.invalidateQueries({
      queryKey: ["collection-membership", source, sourceId],
    })
  }

  const addItem = useMutation({
    mutationFn: (id: number) => CollectionsApi.addItem(id, source, sourceId),
    onSuccess: invalidate,
  })
  const removeItem = useMutation({
    mutationFn: (id: number) => CollectionsApi.removeItem(id, source, sourceId),
    onSuccess: invalidate,
  })
  const createCollection = useMutation({
    mutationFn: (name: string) => CollectionsApi.create(name),
    onSuccess: async (created) => {
      await CollectionsApi.addItem(created.id, source, sourceId)
      setNewName("")
      invalidate()
    },
  })

  // Close on Escape (TG Desktop / browser).
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose()
    }
    window.addEventListener("keydown", onKey)
    return () => window.removeEventListener("keydown", onKey)
  }, [onClose])

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/40">
      <div
        role="dialog"
        aria-label="Add to collection"
        className="w-full max-w-md rounded-t-3xl bg-tg-bg p-4 pb-8 max-h-[80vh] overflow-y-auto"
      >
        <header className="mb-4 flex items-center justify-between">
          <h2 className="text-base font-semibold">Add to collection</h2>
          <button
            type="button"
            aria-label="Close"
            onClick={onClose}
            className="rounded-full p-2 text-tg-hint active:bg-tg-secondary-bg"
          >
            <X className="size-5" />
          </button>
        </header>

        <form
          className="mb-4 flex gap-2"
          onSubmit={(e) => {
            e.preventDefault()
            const trimmed = newName.trim()
            if (!trimmed || createCollection.isPending) return
            createCollection.mutate(trimmed)
          }}
        >
          <input
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            placeholder="New collection name…"
            className="flex-1 rounded-xl bg-tg-secondary-bg px-4 py-3 outline-none"
            maxLength={80}
          />
          <Button
            type="submit"
            size="md"
            disabled={!newName.trim() || createCollection.isPending}
          >
            {createCollection.isPending ? (
              <Loader2 className="size-4 animate-spin" />
            ) : (
              <Plus className="size-4" />
            )}
          </Button>
        </form>

        {collections.isLoading || membership.isLoading ? (
          <div className="flex justify-center py-8">
            <Loader2 className="size-5 animate-spin text-tg-hint" />
          </div>
        ) : collections.data && collections.data.length > 0 ? (
          <ul className="flex flex-col gap-1">
            {collections.data.map((c) => {
              const isIn = inSet.has(c.id)
              const pending =
                (addItem.isPending && addItem.variables === c.id) ||
                (removeItem.isPending && removeItem.variables === c.id)
              return (
                <li key={c.id}>
                  <button
                    type="button"
                    onClick={() =>
                      isIn
                        ? removeItem.mutate(c.id)
                        : addItem.mutate(c.id)
                    }
                    disabled={pending}
                    className="flex w-full items-center justify-between gap-3 rounded-xl px-3 py-3 text-left transition-colors active:bg-tg-secondary-bg"
                  >
                    <div className="min-w-0">
                      <p className="truncate font-medium">{c.name}</p>
                      <p className="text-xs text-tg-hint">
                        {c.item_count} {c.item_count === 1 ? "model" : "models"}
                      </p>
                    </div>
                    <div className="flex size-7 shrink-0 items-center justify-center rounded-full border border-tg-section-bg">
                      {pending ? (
                        <Loader2 className="size-4 animate-spin text-tg-hint" />
                      ) : isIn ? (
                        <Check className="size-4 text-tg-button" />
                      ) : null}
                    </div>
                  </button>
                </li>
              )
            })}
          </ul>
        ) : (
          <p className="py-6 text-center text-sm text-tg-hint">
            No collections yet. Create one above.
          </p>
        )}
      </div>
    </div>
  )
}
