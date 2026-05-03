import { Link } from "react-router-dom"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import { PrinterCard } from "@/components/PrinterCard"
import { Button } from "@/components/ui/button"
import { PrintersApi } from "@/lib/api"

export default function Printers() {
  const qc = useQueryClient()
  const { data: printers, isLoading } = useQuery({
    queryKey: ["printers"],
    queryFn: PrintersApi.list,
  })

  const remove = useMutation({
    mutationFn: (id: number) => PrintersApi.remove(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["printers"] }),
  })

  const handleDelete = (id: number, name: string) => {
    if (window.confirm(`Delete "${name}"?`)) remove.mutate(id)
  }

  return (
    <div className="flex min-h-full flex-col gap-4 px-4 py-6">
      <header className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">My printers</h1>
        <Link to="/printers/new">
          <Button size="sm">Add</Button>
        </Link>
      </header>

      {isLoading ? (
        <p className="text-tg-hint text-sm">Loading...</p>
      ) : printers && printers.length > 0 ? (
        <ul className="flex flex-col gap-3">
          {printers.map((p) => (
            <li key={p.id}>
              <PrinterCard
                printer={p}
                onDelete={(id) => handleDelete(id, p.name)}
                pendingDelete={remove.isPending && remove.variables === p.id}
              />
            </li>
          ))}
        </ul>
      ) : (
        <div className="flex flex-col items-center gap-3 py-12 text-center">
          <p className="text-tg-hint text-sm">No printers yet.</p>
          <Link to="/printers/new">
            <Button>Add your first printer</Button>
          </Link>
        </div>
      )}
    </div>
  )
}
