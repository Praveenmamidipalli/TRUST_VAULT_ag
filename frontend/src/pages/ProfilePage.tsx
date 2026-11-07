import React from 'react';
import { useAuth } from '../contexts/AuthContext';
import { UserCheck, Shield, Key, Lock, CheckCircle2 } from 'lucide-react';

export const ProfilePage: React.FC = () => {
  const { user } = useAuth();

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      <div>
        <h1 className="text-2xl font-bold text-vault-950 tracking-tight">Account Profile & Security</h1>
        <p className="text-sm text-gray-500">
          Identity credentials, assigned enterprise role, and zero-trust policies
        </p>
      </div>

      {/* Profile Card */}
      <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm space-y-6">
        <div className="flex items-center space-x-4 border-b border-gray-100 pb-6">
          <div className="w-14 h-14 bg-vault-900 text-white rounded-2xl flex items-center justify-center font-bold text-xl">
            {user?.username?.substring(0, 2).toUpperCase()}
          </div>
          <div>
            <h2 className="text-lg font-bold text-vault-950">{user?.full_name || user?.username}</h2>
            <div className="text-sm text-gray-400 font-mono">{user?.email}</div>
            <div className="mt-1">
              <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-vault-100 text-vault-800 border border-vault-200">
                {user?.role}
              </span>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-6 text-sm">
          <div>
            <span className="text-xs font-semibold uppercase text-gray-400">Account ID</span>
            <div className="font-mono text-gray-800 mt-1">#{user?.id}</div>
          </div>

          <div>
            <span className="text-xs font-semibold uppercase text-gray-400">Account Status</span>
            <div className="mt-1 flex items-center space-x-1.5 text-green-700 font-semibold text-xs">
              <CheckCircle2 className="w-4 h-4" />
              <span>Active & Authorized</span>
            </div>
          </div>

          <div>
            <span className="text-xs font-semibold uppercase text-gray-400">Password Hashing Algorithm</span>
            <div className="font-mono text-xs text-gray-700 mt-1">Argon2id (RFC 9106 Profile)</div>
          </div>

          <div>
            <span className="text-xs font-semibold uppercase text-gray-400">Registered Since</span>
            <div className="text-xs text-gray-700 mt-1">
              {user ? new Date(user.created_at).toLocaleString() : '-'}
            </div>
          </div>
        </div>
      </div>

      {/* Security Architecture Reference */}
      <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm space-y-4">
        <div className="flex items-center space-x-2 text-vault-950 font-bold">
          <Shield className="w-5 h-5 text-vault-600" />
          <span>TrustVault Architectural Enforcements</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-2">
          <div className="p-4 bg-gray-50 rounded-lg border border-gray-100 space-y-1">
            <div className="flex items-center space-x-1.5 font-semibold text-xs text-vault-950">
              <Lock className="w-4 h-4 text-vault-600" />
              <span>Deny by Default</span>
            </div>
            <p className="text-xs text-gray-500">
              Unshared documents are invisible. System administrators have no automatic backdoor to view customer confidential files.
            </p>
          </div>

          <div className="p-4 bg-gray-50 rounded-lg border border-gray-100 space-y-1">
            <div className="flex items-center space-x-1.5 font-semibold text-xs text-vault-950">
              <Key className="w-4 h-4 text-vault-600" />
              <span>Immediate Revocation</span>
            </div>
            <p className="text-xs text-gray-500">
              Revoking a permission deletes database authorization immediately. No permissions are cached in JWT tokens.
            </p>
          </div>

          <div className="p-4 bg-gray-50 rounded-lg border border-gray-100 space-y-1">
            <div className="flex items-center space-x-1.5 font-semibold text-xs text-vault-950">
              <UserCheck className="w-4 h-4 text-vault-600" />
              <span>Tamper-Evident Ledger</span>
            </div>
            <p className="text-xs text-gray-500">
              Every sensitive action is cryptographically sealed in a SHA-256 hash-chain to guarantee accountability.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
