import { Route, Routes } from "react-router-dom"

import { useBackNav } from "@/lib/backNav"
import CollectionDetail from "@/pages/CollectionDetail"
import Collections from "@/pages/Collections"
import Home from "@/pages/Home"
import Likes from "@/pages/Likes"
import ModelDetail from "@/pages/ModelDetail"
import Onboarding from "@/pages/Onboarding"
import PrinterNew from "@/pages/PrinterNew"
import Printers from "@/pages/Printers"
import Search from "@/pages/Search"

export default function App() {
  useBackNav()
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/onboarding" element={<Onboarding />} />
      <Route path="/printers" element={<Printers />} />
      <Route path="/printers/new" element={<PrinterNew />} />
      <Route path="/search" element={<Search />} />
      <Route path="/models/:source/:id" element={<ModelDetail />} />
      <Route path="/collections" element={<Collections />} />
      <Route path="/collections/:id" element={<CollectionDetail />} />
      <Route path="/likes" element={<Likes />} />
    </Routes>
  )
}
