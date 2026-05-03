import { useState } from "react"
import { Link, useNavigate } from "react-router-dom"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { ArrowLeft, FolderHeart, Loader2, Trash2 } from "lucide-react"

import { Button } from "@/components/ui/button"
import { CollectionsApi, type CollectionListItem } from "@/lib/api"

export default function Collections() {
  const navigate = useNavigate()
  const qc = useQueryClient()
  const [newName, setNewName] = useState("")

  const collections = useQuery({
    queryKey: ["collections"],
    queryFn: CollectionsApi.list,
  })

  const create = useMutation({
    mutationFn: (name: string) => CollectionsApi.create(name),
    onSuccess: () => {
      setNewName("")
      qc.invalidateQueries({ queryKey: ["collections"] })
    },
  })

  const remove = useMutation({
    mutationFn: (id: number) => CollectionsApi.remove(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["collections"] }),
  })

  const handleDelete = (id: number, name: string) => {
    if (
      window.confirm(
        `Delete collection "${name}"? Models inside aren't deleted.`,
      )
    ) {
      remove.mutate(id)
    }
  }

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
        <h1 className="text-base font-medium">Collections</h1>
      </header>

      <form
        className="flex gap-2 px-4 py-3"
        onSubmit={(e) => {
          e.preventDefault()
          const trimmed = newName.trim()
          if (!trimmed || create.isPending) return
          create.mutate(trimmed)
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
          disabled={!newName.trim() || create.isPending}
        >
          Create
        </Button>
      </form>

      <main className="px-4 pb-6">
        {collections.isLoading ? (
          <CenterSpinner />
        ) : collections.data && collections.data.length > 0 ? (
          <ul className="flex flex-col gap-3">
            {collections.data.map((c) => (
              <li key={c.id}>
                <CollectionRow
                  collection={c}
                  onDelete={() => handleDelete(c.id, c.name)}
                  pendingDelete={
                    remove.isPending && remove.variables === c.id
                  }
                />
              </li>
            ))}
          </ul>
        ) : (
          <div className="flex flex-col items-center gap-3 py-16 text-center">
            <FolderHeart className="size-10 text-tg-hint" />
            <p className="text-sm text-tg-hint">
              No collections yet. Create one above to start saving models.
            </p>
          </div>
        )}
      </main>
    </div>
  )
}

function CollectionRow({
  collection,
  onDelete,
  pendingDelete,
}: {
  collection: CollectionListItem
  onDelete: () => void
  pendingDelete: boolean
}) {
  return (
    <article className="relative flex items-center gap-3 rounded-2xl bg-tg-secondary-bg p-3">
      <Link
        to={`/collections/${collection.id}`}
        className="flex flex-1 items-center gap-3 min-w-0"
      >
        <div className="size-14 shrink-0 overflow-hidden rounded-xl bg-tg-section-bg">
          {collection.cover_thumbnail_url ? (
            <img
              src={collection.cover_thumbnail_url}
              alt=""
              className="size-full object-cover"
            />
          ) : (
            <div className="flex size-full items-center justify-center">
              <FolderHeart className="size-6 text-tg-hint" />
            </div>
          )}
        </div>
        <div className="min-w-0">
          <p className="truncate font-medium">{collection.name}</p>
          <p className="text-xs text-tg-hint">
            {collection.item_count}{" "}
            {collection.item_count === 1 ? "model" : "models"}
          </p>
        </div>
      </Link>
      <button
        type="button"
        onClick={onDelete}
        disabled={pendingDelete}
        aria-label={`Delete ${collection.name}`}
        className="rounded-full p-2 text-tg-destructive active:bg-tg-section-bg"
      >
        <Trash2 className="size-4" />
      </button>
    </article>
  )
}

function CenterSpinner() {
  return (
    <div className="flex justify-center py-12">
      <Loader2 className="size-6 animate-spin text-tg-hint" />
    </div>
  )
}
