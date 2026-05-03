import { useMemo } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import { LikesApi, type LikeIdPair } from "@/lib/api"

const KEY = ["likes", "ids"] as const

function asKey(p: { source: string; source_id: string }): string {
  return `${p.source}:${p.source_id}`
}

/** Single per-session query of the user's liked IDs, exposed as a Set for O(1) checks. */
export function useLikedSet() {
  const q = useQuery({
    queryKey: KEY,
    queryFn: LikesApi.ids,
    staleTime: 5 * 60 * 1000, // 5 min — refresh occasionally
  })
  const set = useMemo(
    () => new Set((q.data ?? []).map(asKey)),
    [q.data],
  )
  return { set, isLoading: q.isLoading }
}

export function useToggleLike() {
  const qc = useQueryClient()

  return useMutation({
    mutationFn: async ({
      source,
      sourceId,
      liked,
    }: {
      source: string
      sourceId: string
      liked: boolean
    }) =>
      liked ? LikesApi.unlike(source, sourceId) : LikesApi.like(source, sourceId),

    // Optimistic toggle of the IDs cache so hearts flip instantly.
    onMutate: async ({ source, sourceId, liked }) => {
      await qc.cancelQueries({ queryKey: KEY })
      const prev = qc.getQueryData<LikeIdPair[]>(KEY) ?? []
      const next = liked
        ? prev.filter(
            (p) => !(p.source === source && p.source_id === sourceId),
          )
        : [...prev, { source, source_id: sourceId }]
      qc.setQueryData(KEY, next)
      return { prev }
    },
    onError: (_err, _vars, ctx) => {
      if (ctx?.prev) qc.setQueryData(KEY, ctx.prev)
    },
    onSettled: () => {
      qc.invalidateQueries({ queryKey: KEY })
      // Don't blow caches for search/popular/collection — like_count there is
      // stale until next fetch but heart state is correct via the set.
    },
  })
}
