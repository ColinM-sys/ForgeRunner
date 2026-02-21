import { NavLink } from 'react-router-dom';
import { LayoutDashboard, Upload, CheckSquare, Download, Hammer } from 'lucide-react';

const navItems = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/upload', label: 'Upload', icon: Upload },
  { to: '/review', label: 'Review Queue', icon: CheckSquare },
  { to: '/export', label: 'Export', icon: Download },
];

export default function Sidebar() {
  return (
    <aside className="w-64 bg-gray-900 border-r border-gray-800 flex flex-col">
      <div className="p-4 border-b border-gray-800">
        <div className="flex items-center gap-2">
          <Hammer className="w-6 h-6 text-orange-500" />
          <h1 className="text-xl font-bold text-white">ForgeRunner</h1>
        </div>
        <p className="text-xs text-gray-500 mt-1">Training Data Quality Dashboard</p>
      </div>
      <nav className="flex-1 p-2">
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors ${
                isActive
                  ? 'bg-orange-500/10 text-orange-400'
                  : 'text-gray-400 hover:text-gray-200 hover:bg-gray-800'
              }`
            }
          >
            <item.icon className="w-4 h-4" />
            {item.label}
          </NavLink>
        ))}
      </nav>
      <div className="p-4 border-t border-gray-800 text-xs text-gray-600">
        ForgeRunner v0.1.0
      </div>
    </aside>
  );
}
