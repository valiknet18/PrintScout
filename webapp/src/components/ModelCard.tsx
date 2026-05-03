import { useState } from "react"
import { Link } from "react-router-dom"
import { useQuery } from "@tanstack/react-query"
import {
  Check,
  ExternalLink,
  Heart,
  ImageOff,
  Loader2,
  X,
} from "lucide-react"

import { FitApi, type FitResponse, type SearchHit } from "@/lib/api"
import { useLikedSet, useToggleLike } from "@/lib/likes"

const SOURCE_LABELS: Record<string, string> = {
  printables: "Printables",
  thingiverse: "Thingiverse",
  myminifactory: "MyMiniFactory",
  thangs: "Thangs",
  stlfinder: "STLFinder",
}

export function ModelCard({
  hit,
  printerId,
}: {
  hit: SearchHit
  printerId: number | null
}) {
  const [imgError, setImgError] = useState(false)
  const sourceLabel = SOURCE_LABELS[hit.source] ?? hit.source

  const fit = useQuery({
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
  })

  const { set: likedSet } = useLikedSet()
  const toggleLike = useToggleLike()
  const liked = likedSet.has(`${hit.source}:${hit.source_id}`)
  const baseCount = hit.like_count ?? 0
  // Show optimistic count: if user just liked but server hasn't refreshed
  // search payload yet, +1; if just unliked, -1.
  const optimisticDelta = liked && baseCount === 0 ? 1 : 0
  const displayCount = baseCount + optimisticDelta

  const detailHref = `/models/${encodeURIComponent(hit.source)}/${encodeURIComponent(
    hit.source_id,
  )}${printerId != null ? `?printer_id=${printerId}` : ""}`

  return (
    <Link
      to={detailHref}
      className="group flex flex-col overflow-hidden rounded-2xl bg-tg-secondary-bg text-left transition-opacity active:opacity-80"
    >
      <div className="relative aspect-square w-full overflow-hidden bg-tg-section-bg">
        {hit.thumbnail_url && !imgError ? (
          <img
            src={hit.thumbnail_url}
            alt=""
            loading="lazy"
            onError={() => setImgError(true)}
            className="size-full object-cover"
          />
        ) : (
          <div className="flex size-full items-center justify-center text-tg-hint">
            <ImageOff className="size-8" />
          </div>
        )}
        <div className="absolute left-2 top-2 flex gap-1">
          <Badge>{sourceLabel}</Badge>
          {hit.is_free && <Badge tone="accent">Free</Badge>}
        </div>
        <div className="absolute right-2 top-2">
          <FitBadge fit={fit.data} loading={fit.isLoading} />
        </div>
        <button
          type="button"
          aria-label={liked ? "Unlike" : "Like"}
          onClick={(e) => {
            e.preventDefault()
            e.stopPropagation()
            toggleLike.mutate({
              source: hit.source,
              sourceId: hit.source_id,
              liked,
            })
          }}
          className={`absolute right-2 bottom-2 flex min-w-[2.25rem] items-center justify-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-semibold shadow-lg backdrop-blur-sm transition-colors ${
            liked
              ? "bg-tg-destructive text-white"
              : "bg-white/95 text-tg-destructive"
          }`}
        >
          <Heart
            className={`size-4 ${liked ? "fill-current" : ""}`}
            strokeWidth={2.5}
          />
          {displayCount > 0 && <span>{displayCount}</span>}
        </button>
      </div>

      <div className="flex flex-1 items-start justify-between gap-2 p-3">
        <h3 className="line-clamp-2 text-sm font-medium leading-tight">
          {hit.title}
        </h3>
        <ExternalLink className="size-4 shrink-0 text-tg-hint mt-0.5" />
      </div>
    </Link>
  )
}

function FitBadge({
  fit,
  loading,
}: {
  fit: FitResponse | undefined
  loading: boolean
}) {
  if (loading) {
    return (
      <span className="flex items-center gap-1 rounded-full bg-black/55 px-2 py-0.5 text-[10px] font-medium text-white backdrop-blur-sm">
        <Loader2 className="size-3 animate-spin" />
      </span>
    )
  }
  if (!fit) return null
  if (fit.status === "fits" && fit.bbox) {
    return (
      <span className="flex items-center gap-1 rounded-full bg-emerald-600 px-2 py-0.5 text-[10px] font-medium text-white">
        <Check className="size-3" />
        Fits {Math.round(fit.bbox.x)}×{Math.round(fit.bbox.y)}×
        {Math.round(fit.bbox.z)}
      </span>
    )
  }
  if (fit.status === "too_big" && fit.bbox) {
    return (
      <span className="flex items-center gap-1 rounded-full bg-tg-destructive px-2 py-0.5 text-[10px] font-medium text-white">
        <X className="size-3" />
        {Math.round(fit.bbox.x)}×{Math.round(fit.bbox.y)}×
        {Math.round(fit.bbox.z)}
      </span>
    )
  }
  return (
    <span className="rounded-full bg-black/55 px-2 py-0.5 text-[10px] font-medium text-white/70 backdrop-blur-sm">
      Size unknown
    </span>
  )
}

function Badge({
  children,
  tone = "neutral",
}: {
  children: React.ReactNode
  tone?: "neutral" | "accent"
}) {
  const cls =
    tone === "accent"
      ? "bg-tg-button text-tg-button-text"
      : "bg-black/55 text-white backdrop-blur-sm"
  return (
    <span className={`rounded-full px-2 py-0.5 text-[10px] font-medium ${cls}`}>
      {children}
    </span>
  )
}
