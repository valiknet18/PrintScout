import { useNavigate, useSearchParams } from "react-router-dom"
import { useQuery } from "@tanstack/react-query"
import { ArrowLeft, Heart, Loader2 } from "lucide-react"

import { ModelCard } from "@/components/ModelCard"
import { LikesApi, PrintersApi } from "@/lib/api"

export default function Likes() {
  const navigate = useNavigate()
  const [params] = useSearchParams()

  const liked = useQuery({
    queryKey: ["likes", "list"],
    queryFn: () => LikesApi.list(50),
  })

  const { data: printers } = useQuery({
    queryKey: ["printers"],
    queryFn: PrintersApi.list,
  })

  const printerId =
    Number(params.get("printer_id")) || printers?.[0]?.id || null

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
        <h1 className="text-base font-medium">My likes</h1>
      </header>

      <main className="px-3 pb-6">
        {liked.isLoading ? (
          <CenterSpinner />
        ) : liked.isError ? (
          <Hint text="Couldn't load your likes." />
        ) : liked.data && liked.data.items.length > 0 ? (
          <ul className="grid grid-cols-2 gap-3 pt-2">
            {liked.data.items.map((hit) => (
              <li key={`${hit.source}:${hit.source_id}`}>
                <ModelCard hit={hit} printerId={printerId} />
              </li>
            ))}
          </ul>
        ) : (
          <div className="flex flex-col items-center gap-3 py-16 text-center">
            <Heart className="size-10 text-tg-hint" />
            <p className="text-sm text-tg-hint">
              You haven't liked anything yet. Tap the heart on any model to
              save it here.
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
