import { useState } from 'react'
import { NavLink, Outlet } from 'react-router-dom'

import { useAuth } from '../../hooks/useAuth'

const NAV_ITEMS = [
  { to: '/', label: 'Дашборд', exact: true },
  { to: '/transactions', label: 'Транзакции' },
  { to: '/receipts', label: 'Чеки' },
  { to: '/documents', label: 'Документы' },
  { to: '/counterparties', label: 'Контрагенты' },
  { to: '/reconciliation', label: 'Сверка' },
  { to: '/audit-log', label: 'Журнал' },
  { to: '/settings', label: 'Настройки' },
]

export default function AppShell() {
  const { user, logout } = useAuth()
  const [sidebarOpen, setSidebarOpen] = useState(false)

  return (
    <div className="flex min-h-screen bg-gray-50">
      {/* Mobile overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/20 z-30 md:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      <aside
        className={`fixed inset-y-0 left-0 z-40 w-56 bg-white border-r border-gray-200 flex flex-col
          transform transition-transform duration-200
          md:static md:translate-x-0 md:z-auto
          ${sidebarOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'}`}
      >
        <div className="px-4 py-5 border-b border-gray-200">
          <span className="text-sm font-semibold text-gray-900">Бухгалтер</span>
        </div>
        <nav className="flex-1 py-4 space-y-1 px-2 overflow-y-auto">
          {NAV_ITEMS.map(({ to, label, exact }) => (
            <NavLink
              key={to}
              to={to}
              end={exact}
              onClick={() => setSidebarOpen(false)}
              className={({ isActive }) =>
                `block px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                  isActive
                    ? 'bg-indigo-50 text-indigo-700'
                    : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
                }`
              }
            >
              {label}
            </NavLink>
          ))}
        </nav>
        <div className="px-4 py-4 border-t border-gray-200 text-xs text-gray-500">
          <div className="truncate">{user?.email}</div>
          <button onClick={logout} className="mt-1 text-indigo-600 hover:underline">
            Выйти
          </button>
        </div>
      </aside>

      <main className="flex-1 overflow-auto p-4 md:p-6 min-w-0">
        <button
          className="md:hidden mb-4 p-2 rounded-md text-gray-600 hover:bg-gray-100"
          onClick={() => setSidebarOpen(true)}
          aria-label="Открыть меню"
        >
          ☰
        </button>
        <Outlet />
      </main>
    </div>
  )
}
