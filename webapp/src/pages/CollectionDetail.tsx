import { useNavigate, useParams, useSearchParams } from "react-router-dom"
import { useQuery } from "@tanstack/react-query"
import { ArrowLeft, FolderHeart, Loader2 } from "lucide-react"

import { ModelCard } from "@/components/ModelCard"
import { CollectionsApi, PrintersApi } from "@/lib/api"

export default function CollectionDetail() {
  const navigate = useNavigate()
  const { id = "" } = useParams()
  const [params] = useSearchParams()
  const collectionId = Number(id)
  const printerIdParam = params.get("printer_id")

  const collection = useQuery({
    enabled: Number.isFinite(collectionId),
    queryKey: ["collection", collectionId],
    queryFn: () => CollectionsApi.get(collectionId),
  })

  const { data: printers } = useQuery({
    queryKey: ["printers"],
    queryFn: PrintersApi.list,
  })

  const printerId = printerIdParam
    ? Number(printerIdParam)
    : printers?.[0]?.id ?? null

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
        <h1 className="truncate text-base font-medium">
          {collection.data?.name ?? "Collection"}
        </h1>
      </header>

      <main className="px-3 pb-6">
        {collection.isLoading ? (
          <CenterSpinner />
        ) : collection.isError ? (
          <Hint text="Couldn't load this collection." />
        ) : collection.data && collection.data.items.length > 0 ? (
          <ul className="grid grid-cols-2 gap-3 pt-2">
            {collection.data.items.map((hit) => (
              <li key={`${hit.source}:${hit.source_id}`}>
                <ModelCard hit={hit} printerId={printerId} />
              </li>
            ))}
          </ul>
        ) : (
          <div className="flex flex-col items-center gap-3 py-16 text-center">
            <FolderHeart className="size-10 text-tg-hint" />
            <p className="text-sm text-tg-hint">
              This collection is empty. Open a model and tap "Add to
              collection".
            </p>
          </div>
        )}
      </main>
    </div>
  )
}

function Hint({ text }: { text: string }) {
  return <p className="mt-12 px-4 text-center text-sm text-tg-hint">{text}</p>
}

function CenterSpinner() {
  return (
    <div className="flex justify-center py-12">
      <Loader2 className="size-6 animate-spin text-tg-hint" />
    </div>
  )
}
