import { Link } from 'react-router-dom'

export default function Header() {
  return (
    <header className="bg-white border-b py-3 px-6 flex items-center justify-between">
      <Link to="/" className="text-lg font-semibold text-gray-900 tracking-tight hover:text-gray-700">
        PD Scanner
      </Link>
    </header>
  )
}
