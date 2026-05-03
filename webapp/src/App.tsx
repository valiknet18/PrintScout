import { Route, Routes } from "react-router-dom"

import CollectionDetail from "@/pages/CollectionDetail"
import Collections from "@/pages/Collections"
import Home from "@/pages/Home"
import ModelDetail from "@/pages/ModelDetail"
import Onboarding from "@/pages/Onboarding"
import PrinterNew from "@/pages/PrinterNew"
import Printers from "@/pages/Printers"
import Search from "@/pages/Search"

export default function App() {
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
    </Routes>
  )
}
