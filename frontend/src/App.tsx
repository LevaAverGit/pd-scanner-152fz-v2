import { Routes, Route } from 'react-router-dom'
import Header from './components/Header'
import Footer from './components/Footer'
import DashboardPage from './pages/DashboardPage'
import ScanDetailsPage from './pages/ScanDetailsPage'

export default function App() {
  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      <Header />
      <main className="flex-1">
        <Routes>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/scan/:scan_id" element={<ScanDetailsPage />} />
        </Routes>
      </main>
      <Footer />
    </div>
  )
}
