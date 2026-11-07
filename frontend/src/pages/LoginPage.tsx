import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import api from '../services/api';
import { ShieldCheck, Lock, User, AlertCircle } from 'lucide-react';

export const LoginPage: React.FC = () => {
  const [identifier, setIdentifier] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const res = await api.post('/auth/login', {
        username_or_email: identifier,
        password: password,
      });
      login(res.data.access_token, res.data.user);
      navigate('/');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Login failed. Please check your credentials.');
    } finally {
      setLoading(false);
    }
  };

  const setDemoAccount = (username: string, pass: string) => {
    setIdentifier(username);
    setPassword(pass);
  };

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col justify-center py-12 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-md">
        <div className="flex justify-center">
          <div className="bg-vault-900 p-3 rounded-2xl shadow-lg text-white">
            <ShieldCheck className="w-10 h-10" />
          </div>
        </div>
        <h2 className="mt-4 text-center text-3xl font-extrabold text-vault-950 tracking-tight">
          Trust<span className="text-vault-600">Vault</span>
        </h2>
        <p className="mt-2 text-center text-sm text-gray-600">
          Secure Enterprise Document Sharing & AI Intelligence Platform
        </p>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
        <div className="bg-white py-8 px-4 shadow-xl sm:rounded-2xl sm:px-10 border border-gray-100">
          <form className="space-y-5" onSubmit={handleLogin}>
            {error && (
              <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700 flex items-start space-x-2">
                <AlertCircle className="w-4 h-4 mt-0.5 flex-shrink-0" />
                <span>{error}</span>
              </div>
            )}

            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-gray-700 mb-1">
                Username or Email
              </label>
              <div className="relative rounded-md shadow-sm">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-gray-400">
                  <User className="w-4 h-4" />
                </div>
                <input
                  type="text"
                  required
                  value={identifier}
                  onChange={(e) => setIdentifier(e.target.value)}
                  placeholder="admin or user@trustvault.io"
                  className="block w-full pl-10 pr-3 py-2.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-vault-500 focus:border-vault-500"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-gray-700 mb-1">
                Password
              </label>
              <div className="relative rounded-md shadow-sm">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-gray-400">
                  <Lock className="w-4 h-4" />
                </div>
                <input
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••••••"
                  className="block w-full pl-10 pr-3 py-2.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-vault-500 focus:border-vault-500"
                />
              </div>
            </div>

            <div>
              <button
                type="submit"
                disabled={loading}
                className="w-full flex justify-center py-2.5 px-4 border border-transparent rounded-lg shadow-sm text-sm font-semibold text-white bg-vault-900 hover:bg-vault-800 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-vault-500 disabled:opacity-50 transition-colors"
              >
                {loading ? 'Authenticating...' : 'Sign in to TrustVault'}
              </button>
            </div>
          </form>

          {/* Quick Demo Fill Buttons for Interview Evaluation */}
          <div className="mt-6 pt-6 border-t border-gray-200">
            <span className="block text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2 text-center">
              Quick Demo Logins
            </span>
            <div className="grid grid-cols-3 gap-2">
              <button
                type="button"
                onClick={() => setDemoAccount('admin', 'AdminPass123!')}
                className="py-1 px-2 text-xs font-medium bg-red-50 text-red-700 border border-red-200 rounded hover:bg-red-100 transition-colors"
              >
                Admin Demo
              </button>
              <button
                type="button"
                onClick={() => setDemoAccount('alice_owner', 'OwnerPass123!')}
                className="py-1 px-2 text-xs font-medium bg-blue-50 text-blue-700 border border-blue-200 rounded hover:bg-blue-100 transition-colors"
              >
                Owner Demo
              </button>
              <button
                type="button"
                onClick={() => setDemoAccount('bob_viewer', 'ViewerPass123!')}
                className="py-1 px-2 text-xs font-medium bg-gray-50 text-gray-700 border border-gray-200 rounded hover:bg-gray-100 transition-colors"
              >
                Viewer Demo
              </button>
            </div>
          </div>

          <div className="mt-6 text-center text-sm text-gray-500">
            Need an account?{' '}
            <Link to="/register" className="font-semibold text-vault-600 hover:text-vault-500">
              Create an account
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
};
