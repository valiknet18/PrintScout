import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { useMutation, useQueryClient } from "@tanstack/react-query"

import { Button } from "@/components/ui/button"
import { PrintersApi, type PrinterIn } from "@/lib/api"

const NOZZLE_PRESETS = [0.2, 0.4, 0.6, 0.8]
const MATERIAL_OPTIONS = ["PLA", "PETG", "ABS", "TPU", "ASA", "Nylon", "Resin"]

export default function PrinterNew() {
  const navigate = useNavigate()
  const qc = useQueryClient()
  const [form, setForm] = useState<PrinterIn>({
    name: "",
    kind: "fdm",
    build_x_mm: 220,
    build_y_mm: 220,
    build_z_mm: 250,
    nozzle_mm: 0.4,
    materials: ["PLA"],
  })

  const create = useMutation({
    mutationFn: (p: PrinterIn) => PrintersApi.create(p),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ["printers"] })
      navigate("/")
    },
  })

  const toggleMaterial = (m: string) =>
    setForm((f) => ({
      ...f,
      materials: f.materials.includes(m)
        ? f.materials.filter((x) => x !== m)
        : [...f.materials, m],
    }))

  return (
    <form
      className="flex flex-col gap-5 px-4 py-6"
      onSubmit={(e) => {
        e.preventDefault()
        create.mutate(form)
      }}
    >
      <h1 className="text-xl font-semibold">Add printer</h1>

      <Field label="Name">
        <input
          required
          className="w-full rounded-xl bg-tg-secondary-bg px-4 py-3 outline-none"
          placeholder="Bambu A1 Mini"
          value={form.name}
          onChange={(e) => setForm({ ...form, name: e.target.value })}
        />
      </Field>

      <Field label="Type">
        <div className="flex gap-2">
          {(["fdm", "resin"] as const).map((k) => (
            <button
              key={k}
              type="button"
              onClick={() => setForm({ ...form, kind: k })}
              className={`flex-1 rounded-xl px-4 py-3 capitalize ${
                form.kind === k
                  ? "bg-tg-button text-tg-button-text"
                  : "bg-tg-secondary-bg"
              }`}
            >
              {k.toUpperCase()}
            </button>
          ))}
        </div>
      </Field>

      <Field label="Build volume (mm)">
        <div className="flex gap-2">
          {(["build_x_mm", "build_y_mm", "build_z_mm"] as const).map((k, i) => (
            <input
              key={k}
              type="number"
              required
              min={1}
              className="w-full rounded-xl bg-tg-secondary-bg px-4 py-3 outline-none"
              placeholder={["X", "Y", "Z"][i]}
              value={form[k]}
              onChange={(e) =>
                setForm({ ...form, [k]: Number(e.target.value) })
              }
            />
          ))}
        </div>
      </Field>

      {form.kind === "fdm" && (
        <Field label="Nozzle (mm)">
          <div className="flex flex-wrap gap-2">
            {NOZZLE_PRESETS.map((n) => (
              <button
                key={n}
                type="button"
                onClick={() => setForm({ ...form, nozzle_mm: n })}
                className={`rounded-full px-4 py-2 text-sm ${
                  form.nozzle_mm === n
                    ? "bg-tg-button text-tg-button-text"
                    : "bg-tg-secondary-bg"
                }`}
              >
                {n.toFixed(1)}
              </button>
            ))}
          </div>
        </Field>
      )}

      <Field label="Materials">
        <div className="flex flex-wrap gap-2">
          {MATERIAL_OPTIONS.map((m) => (
            <button
              key={m}
              type="button"
              onClick={() => toggleMaterial(m)}
              className={`rounded-full px-4 py-2 text-sm ${
                form.materials.includes(m)
                  ? "bg-tg-button text-tg-button-text"
                  : "bg-tg-secondary-bg"
              }`}
            >
              {m}
            </button>
          ))}
        </div>
      </Field>

      <Button size="full" type="submit" disabled={create.isPending}>
        {create.isPending ? "Saving..." : "Save printer"}
      </Button>
    </form>
  )
}

function Field({
  label,
  children,
}: {
  label: string
  children: React.ReactNode
}) {
  return (
    <label className="flex flex-col gap-2">
      <span className="px-1 text-xs font-medium uppercase tracking-wide text-tg-section-header">
        {label}
      </span>
      {children}
    </label>
  )
}
