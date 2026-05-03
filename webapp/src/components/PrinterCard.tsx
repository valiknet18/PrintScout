import { Trash2 } from "lucide-react"

import { Button } from "@/components/ui/button"
import type { Printer } from "@/lib/api"

type Props = {
  printer: Printer
  onDelete?: (id: number) => void
  pendingDelete?: boolean
}

export function PrinterCard({ printer, onDelete, pendingDelete }: Props) {
  return (
    <article className="rounded-2xl bg-tg-secondary-bg p-4">
      <header className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <h3 className="truncate text-base font-semibold">{printer.name}</h3>
          <p className="text-xs text-tg-hint mt-0.5 uppercase tracking-wide">
            {printer.kind}
            {printer.nozzle_mm ? ` · ${printer.nozzle_mm.toFixed(1)} mm nozzle` : ""}
          </p>
        </div>
        {onDelete && (
          <Button
            variant="ghost"
            size="sm"
            disabled={pendingDelete}
            onClick={() => onDelete(printer.id)}
            aria-label="Delete printer"
          >
            <Trash2 className="size-4 text-tg-destructive" />
          </Button>
        )}
      </header>

      <p className="mt-3 text-sm">
        <span className="text-tg-hint">Build </span>
        <span className="font-medium">
          {printer.build_x_mm} × {printer.build_y_mm} × {printer.build_z_mm} mm
        </span>
      </p>

      {printer.materials.length > 0 && (
        <ul className="mt-3 flex flex-wrap gap-1.5">
          {printer.materials.map((m) => (
            <li
              key={m}
              className="rounded-full bg-tg-section-bg px-2.5 py-0.5 text-xs"
            >
              {m}
            </li>
          ))}
        </ul>
      )}
    </article>
  )
}
