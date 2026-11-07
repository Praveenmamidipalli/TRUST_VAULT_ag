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
    <aside className="w-64 bg-white border-r border-gray-200 fixed top-16 bottom-0 left-0 overflow-y-auto p-4 flex flex-col justify-between z-20">
      <div className="space-y-1">
        <div className="px-3 py-2 text-xs font-semibold text-gray-400 uppercase tracking-wider">
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
                `flex items-center space-x-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                  isActive
                    ? 'bg-vault-50 text-vault-700 font-semibold'
                    : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
                }`
              }
            >
              <Icon className="w-4 h-4" />
              <span>{item.label}</span>
            </NavLink>
          );
        })}
      </div>

      <div className="p-3 bg-vault-50 border border-vault-100 rounded-lg text-xs text-vault-800">
        <div className="font-semibold mb-1 flex items-center space-x-1">
          <span className="w-2 h-2 rounded-full bg-green-500 inline-block animate-pulse"></span>
          <span>Zero-Trust Enforced</span>
        </div>
        <p className="text-gray-600">Permissions are evaluated live on every access request.</p>
      </div>
    </aside>
  );
};
