import axios from "axios"
import { getInitDataRaw } from "@/lib/tg"

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? "/",
})

api.interceptors.request.use((config) => {
  const initData = getInitDataRaw()
  if (initData) {
    config.headers.Authorization = `tma ${initData}`
  }
  return config
})

export type Printer = {
  id: number
  name: string
  kind: "fdm" | "resin"
  build_x_mm: number
  build_y_mm: number
  build_z_mm: number
  nozzle_mm: number | null
  materials: string[]
}

export type PrinterIn = Omit<Printer, "id">

export const PrintersApi = {
  list: () => api.get<Printer[]>("/api/printers").then((r) => r.data),
  create: (p: PrinterIn) =>
    api.post<Printer>("/api/printers", p).then((r) => r.data),
  remove: (id: number) => api.delete(`/api/printers/${id}`),
}

export type SearchHit = {
  source: string
  source_id: string
  title: string
  url: string
  thumbnail_url: string | null
  is_free: boolean
  tags: string[]
}

export type SearchResponse = {
  total: number
  page: number
  page_size: number
  items: SearchHit[]
  query?: string | null
  original_query?: string | null
}

export type PaidFilter = "free" | "paid" | "all"

export const SearchApi = {
  search: (params: {
    printerId: number
    q: string
    paid?: PaidFilter
    page?: number
    pageSize?: number
  }) =>
    api
      .get<SearchResponse>("/api/search", {
        params: {
          printer_id: params.printerId,
          q: params.q,
          paid: params.paid ?? "free",
          page: params.page ?? 1,
          page_size: params.pageSize ?? 30,
        },
      })
      .then((r) => r.data),
}

export type FitStatus = "fits" | "too_big" | "unknown"

export type FitResponse = {
  status: FitStatus
  bbox: { x: number; y: number; z: number } | null
  margin_pct: number
}

export const FitApi = {
  check: (params: { printerId: number; source: string; sourceId: string }) =>
    api
      .get<FitResponse>("/api/check_fit", {
        params: {
          printer_id: params.printerId,
          source: params.source,
          source_id: params.sourceId,
        },
      })
      .then((r) => r.data),
}

export type ModelFileDetail = {
  file_id: string
  file_url: string
  fmt: string
  bbox: { x: number; y: number; z: number } | null
}

export type ModelDetail = {
  source: string
  source_id: string
  title: string
  url: string
  thumbnail_url: string | null
  is_free: boolean
  tags: string[]
  files: ModelFileDetail[]
}

export const ModelApi = {
  get: (source: string, sourceId: string) =>
    api
      .get<ModelDetail>(
        `/api/model/${encodeURIComponent(source)}/${encodeURIComponent(sourceId)}`,
      )
      .then((r) => r.data),
}

export type PopularResponse = {
  items: SearchHit[]
}

export const PopularApi = {
  list: (limit = 24) =>
    api
      .get<PopularResponse>("/api/popular", { params: { limit } })
      .then((r) => r.data),
}
