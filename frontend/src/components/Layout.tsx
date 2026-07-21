import { NavLink, Outlet } from 'react-router-dom';
import { StatusBar } from './StatusBar';

const navItems = [
  { to: '/voice-design', icon: '✨', label: '声音设计' },
  { to: '/voice-clone', icon: '🎭', label: '声音克隆' },
  { to: '/debug', icon: '🔬', label: '调试台' },
  { to: '/library', icon: '📚', label: '音色库' },
];

export function Layout() {
  return (
    <div className="flex h-screen overflow-hidden">
      <aside className="w-60 bg-white border-r border-gray-100 flex flex-col py-7 px-5 gap-1.5 shrink-0">
        <div className="text-lg font-bold text-gray-900 mb-7 flex items-center gap-2">
          <span className="text-xl">🎙️</span> TTS Studio
        </div>
        {navItems.map(item => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) =>
              `flex items-center gap-2.5 px-4 py-3 rounded-xl text-[15px] font-medium transition-colors ${
                isActive ? 'bg-violet-50 text-violet-600' : 'text-gray-500 hover:bg-gray-50 hover:text-gray-900'
              }`
            }
          >
            <span className="w-5 text-center">{item.icon}</span>
            {item.label}
          </NavLink>
        ))}
        <div className="mt-auto">
          <StatusBar />
        </div>
      </aside>
      <main className="flex-1 overflow-y-auto py-9 px-11">
        <Outlet />
      </main>
    </div>
  );
}
