import { useState } from "react"
import { useNavigate, useParams, useSearchParams } from "react-router-dom"
import { useQuery } from "@tanstack/react-query"
import {
  ArrowLeft,
  Check,
  ExternalLink,
  ImageOff,
  Loader2,
  X,
} from "lucide-react"

import { Button } from "@/components/ui/button"
import {
  FitApi,
  ModelApi,
  PrintersApi,
  type FitResponse,
  type ModelDetail as ModelDetailT,
  type Printer,
} from "@/lib/api"
import { openExternalLink } from "@/lib/tg"

const SOURCE_LABELS: Record<string, string> = {
  printables: "Printables",
  thingiverse: "Thingiverse",
  myminifactory: "MyMiniFactory",
  thangs: "Thangs",
  stlfinder: "STLFinder",
}

export default function ModelDetail() {
  const navigate = useNavigate()
  const { source = "", id = "" } = useParams()
  const [params] = useSearchParams()
  const printerIdParam = params.get("printer_id")
  const printerId = printerIdParam ? Number(printerIdParam) : null

  const model = useQuery({
    queryKey: ["model", source, id],
    queryFn: () => ModelApi.get(source, id),
  })

  const { data: printers } = useQuery({
    queryKey: ["printers"],
    queryFn: PrintersApi.list,
  })
  const printer = printers?.find((p) => p.id === printerId) ?? null

  const fit = useQuery({
    enabled: printerId != null && model.isSuccess,
    queryKey: ["fit", printerId, source, id],
    queryFn: () =>
      FitApi.check({ printerId: printerId!, source, sourceId: id }),
    staleTime: Infinity,
    retry: false,
  })

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
        <h1 className="truncate text-base font-medium">Model</h1>
      </header>

      {model.isLoading ? (
        <CenterSpinner />
      ) : model.isError ? (
        <Hint text={`Couldn't load model: ${(model.error as Error).message}`} />
      ) : model.data ? (
        <Body model={model.data} printer={printer} fit={fit.data} fitLoading={fit.isLoading} />
      ) : null}
    </div>
  )
}

function Body({
  model,
  printer,
  fit,
  fitLoading,
}: {
  model: ModelDetailT
  printer: Printer | null
  fit: FitResponse | undefined
  fitLoading: boolean
}) {
  const [imgError, setImgError] = useState(false)
  const sourceLabel = SOURCE_LABELS[model.source] ?? model.source

  return (
    <div className="flex flex-col gap-4 px-4 pb-8">
      <div className="relative -mx-4 aspect-[4/3] overflow-hidden bg-tg-secondary-bg">
        {model.thumbnail_url && !imgError ? (
          <img
            src={model.thumbnail_url}
            alt=""
            onError={() => setImgError(true)}
            className="size-full object-cover"
          />
        ) : (
          <div className="flex size-full items-center justify-center text-tg-hint">
            <ImageOff className="size-12" />
          </div>
        )}
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <span className="rounded-full bg-tg-secondary-bg px-3 py-1 text-xs font-medium">
          {sourceLabel}
        </span>
        {model.is_free && (
          <span className="rounded-full bg-tg-button px-3 py-1 text-xs font-medium text-tg-button-text">
            Free
          </span>
        )}
        <FitInline fit={fit} loading={fitLoading} printer={printer} />
      </div>

      <h2 className="text-lg font-semibold leading-tight">{model.title}</h2>

      <Button
        size="full"
        onClick={() => openExternalLink(model.url)}
        className="gap-2"
      >
        Open on {sourceLabel}
        <ExternalLink className="size-4" />
      </Button>

      <FitDetails fit={fit} printer={printer} loading={fitLoading} />

      {model.files.length > 0 && (
        <section>
          <h3 className="mb-2 text-xs font-medium uppercase tracking-wide text-tg-section-header">
            Files
          </h3>
          <ul className="flex flex-col gap-2">
            {model.files.map((f) => (
              <li
                key={f.file_id}
                className="flex items-center justify-between rounded-xl bg-tg-secondary-bg px-3 py-2.5 text-sm"
              >
                <div className="min-w-0">
                  <p className="truncate font-medium">
                    {f.file_id} <span className="text-tg-hint">.{f.fmt}</span>
                  </p>
                  {f.bbox && (
                    <p className="text-xs text-tg-hint">
                      {Math.round(f.bbox.x)} × {Math.round(f.bbox.y)} ×{" "}
                      {Math.round(f.bbox.z)} mm
                    </p>
                  )}
                </div>
              </li>
            ))}
          </ul>
        </section>
      )}

      {model.tags.length > 0 && (
        <section>
          <h3 className="mb-2 text-xs font-medium uppercase tracking-wide text-tg-section-header">
            Tags
          </h3>
          <ul className="flex flex-wrap gap-1.5">
            {model.tags.slice(0, 30).map((t) => (
              <li
                key={t}
                className="rounded-full bg-tg-secondary-bg px-2.5 py-0.5 text-xs"
              >
                {t}
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  )
}

function FitInline({
  fit,
  loading,
  printer,
}: {
  fit: FitResponse | undefined
  loading: boolean
  printer: Printer | null
}) {
  if (!printer) return null
  if (loading) {
    return (
      <span className="flex items-center gap-1 rounded-full bg-tg-secondary-bg px-3 py-1 text-xs">
        <Loader2 className="size-3 animate-spin" />
        Checking fit...
      </span>
    )
  }
  if (!fit) return null
  if (fit.status === "fits") {
    return (
      <span className="flex items-center gap-1 rounded-full bg-emerald-600 px-3 py-1 text-xs font-medium text-white">
        <Check className="size-3" />
        Fits {printer.name}
      </span>
    )
  }
  if (fit.status === "too_big") {
    return (
      <span className="flex items-center gap-1 rounded-full bg-tg-destructive px-3 py-1 text-xs font-medium text-white">
        <X className="size-3" />
        Too big for {printer.name}
      </span>
    )
  }
  return (
    <span className="rounded-full bg-tg-secondary-bg px-3 py-1 text-xs text-tg-hint">
      Size unknown
    </span>
  )
}

function FitDetails({
  fit,
  printer,
  loading,
}: {
  fit: FitResponse | undefined
  printer: Printer | null
  loading: boolean
}) {
  if (!printer || loading || !fit?.bbox) return null
  return (
    <section className="rounded-2xl bg-tg-secondary-bg p-4">
      <h3 className="mb-3 text-xs font-medium uppercase tracking-wide text-tg-section-header">
        Fit
      </h3>
      <div className="grid grid-cols-3 gap-3 text-sm">
        <Stat label="Model" value={`${Math.round(fit.bbox.x)}×${Math.round(fit.bbox.y)}×${Math.round(fit.bbox.z)}`} />
        <Stat label={printer.name} value={`${printer.build_x_mm}×${printer.build_y_mm}×${printer.build_z_mm}`} />
        <Stat label="Margin" value={`${fit.margin_pct}%`} />
      </div>
    </section>
  )
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-0">
      <p className="text-xs text-tg-hint truncate">{label}</p>
      <p className="font-medium truncate">{value}</p>
    </div>
  )
}

function Hint({ text }: { text: string }) {
  return <p className="mt-12 px-4 text-center text-sm text-tg-hint">{text}</p>
}

function CenterSpinner() {
  return (
    <div className="mt-12 flex justify-center">
      <Loader2 className="size-6 animate-spin text-tg-hint" />
    </div>
  )
}
