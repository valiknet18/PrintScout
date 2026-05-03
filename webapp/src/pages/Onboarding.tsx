import { Link } from "react-router-dom"
import { Printer } from "lucide-react"

import { Button } from "@/components/ui/button"

export default function Onboarding() {
  return (
    <div className="flex min-h-full flex-col items-center justify-center gap-6 px-6 text-center">
      <div className="rounded-2xl bg-tg-secondary-bg p-6">
        <Printer className="size-12 text-tg-link" />
      </div>
      <h1 className="text-2xl font-semibold">Welcome to PrintScout</h1>
      <p className="text-tg-hint max-w-sm">
        Add your 3D printer once and find models that actually fit on your bed.
      </p>
      <Link to="/printers/new" className="w-full max-w-sm">
        <Button size="full">Add my first printer</Button>
      </Link>
    </div>
  )
}
