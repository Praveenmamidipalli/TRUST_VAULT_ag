import React from 'react';
import { useAuth } from '../contexts/AuthContext';
import { ShieldCheck, LogOut, User as UserIcon } from 'lucide-react';
import { Link } from 'react-router-dom';

export const Navbar: React.FC = () => {
  const { user, logout } = useAuth();

  const getRoleBadge = () => {
    switch (user?.role) {
      case 'ADMIN':
        return <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-red-100 text-red-800 border border-red-200">ADMIN</span>;
      case 'OWNER':
        return <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-100 text-blue-800 border border-blue-200">OWNER</span>;
      case 'VIEWER':
      default:
        return <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-gray-100 text-gray-700 border border-gray-200">VIEWER</span>;
    }
  };

  return (
    <header className="bg-white border-b border-gray-200 h-16 fixed top-0 left-0 right-0 z-30 flex items-center justify-between px-6">
      <div className="flex items-center space-x-3">
        <div className="bg-vault-900 p-2 rounded-lg text-white">
          <ShieldCheck className="w-5 h-5" />
        </div>
        <Link to="/" className="text-xl font-bold tracking-tight text-vault-950">
          Trust<span className="text-vault-600">Vault</span>
        </Link>
        <span className="hidden sm:inline-block text-xs uppercase tracking-wider text-gray-400 font-medium ml-2">
          Enterprise Security
        </span>
      </div>

      <div className="flex items-center space-x-4">
        {user && (
          <div className="flex items-center space-x-3">
            {getRoleBadge()}
            <div className="flex items-center space-x-2 text-sm text-gray-700">
              <UserIcon className="w-4 h-4 text-gray-400" />
              <span className="font-medium">{user.full_name || user.username}</span>
            </div>
            <button
              onClick={logout}
              className="text-gray-500 hover:text-red-600 p-1.5 rounded-md hover:bg-gray-100 transition-colors"
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
