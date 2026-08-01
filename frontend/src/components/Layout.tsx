import { NavLink, Outlet } from 'react-router-dom'
import { DbHealthBadge } from './DbHealthBadge'
import { ProjectSwitcher } from './ProjectSwitcher'

const NAV_ITEMS = [
  { to: '/', label: 'Dashboard', end: true },
  { to: '/projects', label: 'Projects' },
  { to: '/inspection', label: 'Inspection Reports' },
  { to: '/ai-reasoning', label: 'AI Reasoning' },
  { to: '/nlp', label: 'NLP' },
  { to: '/ml-prediction', label: 'ML Prediction' },
  { to: '/deep-learning-vision', label: 'Deep Learning Vision' },
  { to: '/memory', label: 'Memory' },
  { to: '/settings', label: 'Feature Flags / Settings' },
]

export function Layout() {
  return (
    <div className="flex min-h-screen">
      <aside className="flex w-64 shrink-0 flex-col border-r border-vidur-border bg-vidur-surface">
        <div className="border-b border-vidur-border px-5 py-4">
          <p className="text-lg font-semibold text-vidur-text">VIDUR</p>
          <p className="text-xs text-vidur-text-muted">Project Watchdog</p>
        </div>
        <nav className="flex-1 space-y-1 px-3 py-4">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) =>
                `block rounded-md px-3 py-2 text-sm transition ${
                  isActive
                    ? 'bg-vidur-accent-muted text-vidur-text'
                    : 'text-vidur-text-muted hover:bg-vidur-surface-raised hover:text-vidur-text'
                }`
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
      </aside>

      <div className="flex flex-1 flex-col">
        <header className="flex items-center justify-end gap-3 border-b border-vidur-border bg-vidur-surface px-6 py-3">
          <DbHealthBadge />
          <ProjectSwitcher />
        </header>
        <main className="flex-1 overflow-y-auto p-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
