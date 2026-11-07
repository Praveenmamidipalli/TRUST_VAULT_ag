import React, { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import api from '../services/api';
import { User, UserRole } from '../types';
import { Search, CheckCircle2, XCircle } from 'lucide-react';

export const AdminUsersPage: React.FC = () => {
  const { user: currentUser } = useAuth();
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [updatingId, setUpdatingId] = useState<number | null>(null);

  const fetchUsers = async () => {
    try {
      setLoading(true);
      const res = await api.get<User[]>('/admin/users', {
        params: search ? { q: search } : undefined,
      });
      setUsers(res.data);
    } catch (err) {
      console.error('Failed to load users', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUsers();
  }, [search]);

  const handleRoleChange = async (userId: number, newRole: UserRole) => {
    setUpdatingId(userId);
    try {
      const res = await api.patch<User>(`/admin/users/${userId}`, { role: newRole });
      setUsers(users.map((u) => (u.id === userId ? res.data : u)));
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to update user role.');
    } finally {
      setUpdatingId(null);
    }
  };

  const handleStatusToggle = async (userId: number, currentStatus: boolean) => {
    if (userId === currentUser?.id && currentStatus) {
      alert('Security Protection: You cannot deactivate your own administrative account.');
      return;
    }

    setUpdatingId(userId);
    try {
      const res = await api.patch<User>(`/admin/users/${userId}`, { is_active: !currentStatus });
      setUsers(users.map((u) => (u.id === userId ? res.data : u)));
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to update user status.');
    } finally {
      setUpdatingId(null);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-vault-950 tracking-tight">Enterprise User Administration</h1>
          <p className="text-sm text-gray-500">
            Manage corporate identities, assign access roles, and control account active status
          </p>
        </div>
      </div>

      {/* Search Toolbar */}
      <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm flex items-center justify-between">
        <div className="relative w-full md:w-80">
          <Search className="w-4 h-4 absolute left-3 top-3 text-gray-400" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search users by name, username or email..."
            className="w-full pl-9 pr-4 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-vault-500"
          />
        </div>
        <div className="text-xs text-gray-400 font-medium">
          Total Users: {users.length}
        </div>
      </div>

      {/* Users Table */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
        {loading ? (
          <div className="p-12 text-center text-sm text-gray-400">Loading user accounts...</div>
        ) : users.length === 0 ? (
          <div className="p-12 text-center text-sm text-gray-400">No matching user accounts.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-gray-50 text-gray-500 text-xs font-semibold uppercase tracking-wider">
                <tr>
                  <th className="px-6 py-3.5">User</th>
                  <th className="px-6 py-3.5">Email</th>
                  <th className="px-6 py-3.5">Assigned Role</th>
                  <th className="px-6 py-3.5">Status</th>
                  <th className="px-6 py-3.5">Registered</th>
                  <th className="px-6 py-3.5 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {users.map((u) => {
                  const isSelf = u.id === currentUser?.id;
                  return (
                    <tr key={u.id} className="hover:bg-gray-50/75 transition-colors">
                      <td className="px-6 py-4">
                        <div className="font-semibold text-vault-950 flex items-center space-x-2">
                          <span>{u.username}</span>
                          {isSelf && (
                            <span className="text-[10px] font-bold uppercase tracking-wider bg-vault-100 text-vault-800 px-1.5 py-0.2 rounded">
                              You
                            </span>
                          )}
                        </div>
                        <div className="text-xs text-gray-400">{u.full_name || 'No full name'}</div>
                      </td>

                      <td className="px-6 py-4 text-xs font-mono text-gray-600">
                        {u.email}
                      </td>

                      <td className="px-6 py-4">
                        <select
                          value={u.role}
                          disabled={updatingId === u.id || (isSelf && u.role === 'ADMIN')}
                          onChange={(e) => handleRoleChange(u.id, e.target.value as UserRole)}
                          className="px-2.5 py-1 text-xs font-semibold rounded-md border border-gray-300 bg-white focus:outline-none focus:ring-2 focus:ring-vault-500 disabled:opacity-50"
                        >
                          <option value="VIEWER">VIEWER</option>
                          <option value="OWNER">OWNER</option>
                          <option value="ADMIN">ADMIN</option>
                        </select>
                      </td>

                      <td className="px-6 py-4">
                        <span className={`inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-xs font-semibold ${
                          u.is_active ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'
                        }`}>
                          {u.is_active ? <CheckCircle2 className="w-3.5 h-3.5" /> : <XCircle className="w-3.5 h-3.5" />}
                          <span>{u.is_active ? 'Active' : 'Deactivated'}</span>
                        </span>
                      </td>

                      <td className="px-6 py-4 text-xs text-gray-500">
                        {new Date(u.created_at).toLocaleDateString()}
                      </td>

                      <td className="px-6 py-4 text-right">
                        <button
                          onClick={() => handleStatusToggle(u.id, u.is_active)}
                          disabled={updatingId === u.id || isSelf}
                          className={`px-3 py-1 text-xs font-semibold rounded-md transition-colors ${
                            u.is_active
                              ? 'border border-red-200 text-red-700 hover:bg-red-50 disabled:opacity-40'
                              : 'border border-green-200 text-green-700 hover:bg-green-50 disabled:opacity-40'
                          }`}
                        >
                          {u.is_active ? 'Deactivate' : 'Activate'}
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
