import { NavLink, Outlet } from 'react-router-dom'
import { useAuth } from '../../hooks/useAuth'

const NAV_ITEMS = [
  { to: '/', label: 'Дашборд', exact: true },
  { to: '/transactions', label: 'Транзакции' },
  { to: '/receipts', label: 'Чеки' },
  { to: '/reconciliation', label: 'Сверка' },
  { to: '/settings', label: 'Настройки' },
]

export default function AppShell() {
  const { user, logout } = useAuth()

  return (
    <div className="flex min-h-screen bg-gray-50">
      <aside className="w-56 bg-white border-r border-gray-200 flex flex-col">
        <div className="px-4 py-5 border-b border-gray-200">
          <span className="text-sm font-semibold text-gray-900">Бухгалтер</span>
        </div>
        <nav className="flex-1 py-4 space-y-1 px-2">
          {NAV_ITEMS.map(({ to, label, exact }) => (
            <NavLink
              key={to}
              to={to}
              end={exact}
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
          <button
            onClick={logout}
            className="mt-1 text-indigo-600 hover:underline"
          >
            Выйти
          </button>
        </div>
      </aside>
      <main className="flex-1 overflow-auto p-6">
        <Outlet />
      </main>
    </div>
  )
}
