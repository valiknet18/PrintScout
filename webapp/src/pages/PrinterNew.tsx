import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { useMutation, useQueryClient } from "@tanstack/react-query"

import { Button } from "@/components/ui/button"
import { PrintersApi, type PrinterIn } from "@/lib/api"

const NOZZLE_PRESETS = [0.2, 0.4, 0.6, 0.8]
const MATERIAL_OPTIONS = ["PLA", "PETG", "ABS", "TPU", "ASA", "Nylon", "Resin"]

type VolumePreset = { label: string; x: number; y: number; z: number }

const VOLUME_PRESETS: VolumePreset[] = [
  { label: "Mini", x: 180, y: 180, z: 180 },
  { label: "Standard", x: 220, y: 220, z: 250 },
  { label: "Bambu A1/P1", x: 256, y: 256, z: 256 },
  { label: "Prusa MK4", x: 250, y: 210, z: 220 },
  { label: "Large 300", x: 300, y: 300, z: 300 },
  { label: "XL", x: 350, y: 350, z: 400 },
]

export default function PrinterNew() {
  const navigate = useNavigate()
  const qc = useQueryClient()

  const [name, setName] = useState("")
  const [kind, setKind] = useState<"fdm" | "resin">("fdm")
  // X/Y/Z held as strings so clearing the input shows empty, not "0".
  const [x, setX] = useState("220")
  const [y, setY] = useState("220")
  const [z, setZ] = useState("250")
  const [nozzle, setNozzle] = useState<number | null>(0.4)
  const [materials, setMaterials] = useState<string[]>(["PLA"])

  const create = useMutation({
    mutationFn: (p: PrinterIn) => PrintersApi.create(p),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ["printers"] })
      navigate("/")
    },
  })

  const toggleMaterial = (m: string) =>
    setMaterials((curr) =>
      curr.includes(m) ? curr.filter((x) => x !== m) : [...curr, m],
    )

  const isPresetActive = (p: VolumePreset) =>
    Number(x) === p.x && Number(y) === p.y && Number(z) === p.z

  const applyPreset = (p: VolumePreset) => {
    setX(String(p.x))
    setY(String(p.y))
    setZ(String(p.z))
  }

  const xN = Number(x)
  const yN = Number(y)
  const zN = Number(z)
  const dimsValid =
    Number.isFinite(xN) && xN > 0 &&
    Number.isFinite(yN) && yN > 0 &&
    Number.isFinite(zN) && zN > 0

  const canSubmit = name.trim().length > 0 && dimsValid && !create.isPending

  return (
    <form
      className="flex flex-col gap-5 px-4 py-6"
      onSubmit={(e) => {
        e.preventDefault()
        if (!canSubmit) return
        create.mutate({
          name: name.trim(),
          kind,
          build_x_mm: xN,
          build_y_mm: yN,
          build_z_mm: zN,
          nozzle_mm: kind === "fdm" ? nozzle : null,
          materials,
        })
      }}
    >
      <h1 className="text-xl font-semibold">Add printer</h1>

      <Field label="Name">
        <input
          required
          className="w-full rounded-xl bg-tg-secondary-bg px-4 py-3 outline-none"
          placeholder="Bambu A1 Mini"
          value={name}
          onChange={(e) => setName(e.target.value)}
        />
      </Field>

      <Field label="Type">
        <div className="flex gap-2">
          {(["fdm", "resin"] as const).map((k) => (
            <button
              key={k}
              type="button"
              onClick={() => setKind(k)}
              className={`flex-1 rounded-xl px-4 py-3 capitalize ${
                kind === k
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
        <ul className="flex flex-wrap gap-2">
          {VOLUME_PRESETS.map((p) => {
            const active = isPresetActive(p)
            return (
              <li key={p.label}>
                <button
                  type="button"
                  onClick={() => applyPreset(p)}
                  className={`flex flex-col items-start rounded-xl px-3 py-2 text-left text-xs leading-tight transition-colors ${
                    active
                      ? "bg-tg-button text-tg-button-text"
                      : "bg-tg-secondary-bg text-tg-text"
                  }`}
                >
                  <span className="font-medium">{p.label}</span>
                  <span className={active ? "opacity-90" : "text-tg-hint"}>
                    {p.x}×{p.y}×{p.z}
                  </span>
                </button>
              </li>
            )
          })}
        </ul>

        <div className="mt-3 flex gap-2">
          <DimInput axis="X" value={x} onChange={setX} />
          <DimInput axis="Y" value={y} onChange={setY} />
          <DimInput axis="Z" value={z} onChange={setZ} />
        </div>
      </Field>

      {kind === "fdm" && (
        <Field label="Nozzle (mm)">
          <div className="flex flex-wrap gap-2">
            {NOZZLE_PRESETS.map((n) => (
              <button
                key={n}
                type="button"
                onClick={() => setNozzle(n)}
                className={`rounded-full px-4 py-2 text-sm ${
                  nozzle === n
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
                materials.includes(m)
                  ? "bg-tg-button text-tg-button-text"
                  : "bg-tg-secondary-bg"
              }`}
            >
              {m}
            </button>
          ))}
        </div>
      </Field>

      <Button size="full" type="submit" disabled={!canSubmit}>
        {create.isPending ? "Saving..." : "Save printer"}
      </Button>
    </form>
  )
}

function DimInput({
  axis,
  value,
  onChange,
}: {
  axis: "X" | "Y" | "Z"
  value: string
  onChange: (next: string) => void
}) {
  return (
    <label className="relative flex-1">
      <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-xs font-medium text-tg-hint">
        {axis}
      </span>
      <input
        // text + inputMode keeps the field cleanly empty when the user
        // deletes the value (type="number" inserts NaN/0 quirks).
        type="text"
        inputMode="decimal"
        autoComplete="off"
        placeholder="—"
        value={value}
        onChange={(e) => {
          const next = e.target.value.replace(/[^\d.]/g, "")
          onChange(next)
        }}
        className="w-full rounded-xl bg-tg-secondary-bg pl-7 pr-3 py-3 outline-none"
      />
    </label>
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
