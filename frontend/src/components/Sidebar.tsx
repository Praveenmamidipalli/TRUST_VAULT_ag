import React from 'react';
import { NavLink } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { 
  LayoutDashboard, 
  Files, 
  Bot, 
  History, 
  Users, 
  UserCheck
} from 'lucide-react';

export const Sidebar: React.FC = () => {
  const { user } = useAuth();
  const isAdmin = user?.role === 'ADMIN';

  const navItems = [
    { to: '/', label: 'Dashboard', icon: LayoutDashboard },
    { to: '/documents', label: 'Document Library', icon: Files },
    { to: '/ai', label: 'AI Intelligence', icon: Bot },
    ...(isAdmin ? [
      { to: '/audit', label: 'Audit Trail', icon: History },
      { to: '/admin/users', label: 'User Management', icon: Users },
    ] : []),
    { to: '/profile', label: 'Account Profile', icon: UserCheck },
  ];

  return (
    <aside className="w-64 bg-white/95 backdrop-blur-md border-r border-sky-100 fixed top-16 bottom-0 left-0 overflow-y-auto p-4 flex flex-col justify-between z-20 shadow-xs">
      <div className="space-y-1">
        <div className="px-3 py-2 text-xs font-semibold text-slate-400 uppercase tracking-wider">
          Workspace
        </div>
        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === '/'}
              className={({ isActive }) =>
                `flex items-center space-x-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all ${
                  isActive
                    ? 'bg-gradient-to-r from-sky-50 to-blue-50 text-sky-700 font-semibold shadow-xs border border-sky-100'
                    : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'
                }`
              }
            >
              <Icon className="w-4 h-4 text-sky-600" />
              <span>{item.label}</span>
            </NavLink>
          );
        })}
      </div>

      <div className="p-3.5 bg-gradient-to-br from-sky-50/70 to-blue-50/50 border border-sky-100 rounded-xl text-xs text-sky-900 shadow-xs">
        <div className="font-semibold mb-1 flex items-center space-x-1.5">
          <span className="w-2 h-2 rounded-full bg-emerald-500 inline-block animate-pulse"></span>
          <span>Zero-Trust Enforced</span>
        </div>
        <p className="text-[11px] text-slate-500 leading-relaxed">
          Database access policies verified per request with instant revocation.
        </p>
      </div>
    </aside>
  );
};
