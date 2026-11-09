import React from 'react';
import { useAuth } from '../contexts/AuthContext';
import { ShieldCheck, LogOut, User as UserIcon } from 'lucide-react';
import { Link } from 'react-router-dom';

export const Navbar: React.FC = () => {
  const { user, logout } = useAuth();

  const getRoleBadge = () => {
    switch (user?.role) {
      case 'ADMIN':
        return <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-rose-50 text-rose-700 border border-rose-200">ADMIN</span>;
      case 'OWNER':
        return <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-sky-50 text-sky-700 border border-sky-200">OWNER</span>;
      case 'VIEWER':
      default:
        return <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">VIEWER</span>;
    }
  };

  return (
    <header className="bg-white/90 backdrop-blur-md border-b border-sky-100 h-16 fixed top-0 left-0 right-0 z-30 flex items-center justify-between px-6 shadow-xs">
      <div className="flex items-center space-x-3">
        <div className="bg-gradient-to-tr from-sky-600 to-blue-700 p-2 rounded-xl text-white shadow-sm shadow-sky-500/20">
          <ShieldCheck className="w-5 h-5" />
        </div>
        <Link to="/" className="text-xl font-bold tracking-tight text-slate-900">
          Trust<span className="text-sky-600 font-extrabold">Vault</span>
        </Link>
        <span className="hidden sm:inline-block text-[11px] uppercase tracking-widest text-sky-700/80 font-semibold bg-sky-50 px-2 py-0.5 rounded-md border border-sky-100 ml-2">
          Enterprise Security
        </span>
      </div>

      <div className="flex items-center space-x-4">
        {user && (
          <div className="flex items-center space-x-3">
            {getRoleBadge()}
            <div className="flex items-center space-x-2 text-sm text-slate-700 bg-slate-50 px-3 py-1.5 rounded-full border border-slate-200/60">
              <UserIcon className="w-4 h-4 text-sky-600" />
              <span className="font-medium text-xs sm:text-sm">{user.full_name || user.username}</span>
            </div>
            <button
              onClick={logout}
              className="text-slate-400 hover:text-rose-600 p-1.5 rounded-lg hover:bg-rose-50 transition-colors"
              title="Sign Out"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        )}
      </div>
    </header>
  );
};
