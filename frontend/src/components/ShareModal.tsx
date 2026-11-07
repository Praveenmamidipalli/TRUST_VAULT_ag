import React, { useState, useEffect } from 'react';
import { X, UserPlus, Trash2, ShieldCheck, AlertCircle } from 'lucide-react';
import api from '../services/api';
import { Document, DocumentPermission, PermissionLevel, User } from '../types';

interface ShareModalProps {
  document: Document;
  isOpen: boolean;
  onClose: () => void;
}

export const ShareModal: React.FC<ShareModalProps> = ({ document, isOpen, onClose }) => {
  const [permissions, setPermissions] = useState<DocumentPermission[]>([]);
  const [users, setUsers] = useState<User[]>([]);
  const [selectedUserId, setSelectedUserId] = useState<number | ''>('');
  const [permissionLevel, setPermissionLevel] = useState<PermissionLevel>('READ');
  const [loading, setLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const fetchPermissions = async () => {
    try {
      setLoading(true);
      const res = await api.get<DocumentPermission[]>(`/documents/${document.id}/permissions`);
      setPermissions(res.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load permissions.');
    } finally {
      setLoading(false);
    }
  };

  const fetchUsers = async () => {
    try {
      // Fetch users list for selection (or search)
      const res = await api.get<User[]>('/admin/users');
      // Filter out owner
      setUsers(res.data.filter((u) => u.id !== document.owner_id));
    } catch {
      // If non-admin owner cannot list /admin/users, user can still input user ID
    }
  };

  useEffect(() => {
    if (isOpen) {
      fetchPermissions();
      fetchUsers();
      setError(null);
      setSuccess(null);
    }
  }, [isOpen, document.id]);

  if (!isOpen) return null;

  const handleGrant = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedUserId) {
      setError('Please select or specify a user ID to grant permission.');
      return;
    }

    setActionLoading(true);
    setError(null);
    setSuccess(null);

    try {
      await api.post(`/documents/${document.id}/permissions`, {
        user_id: Number(selectedUserId),
        permission_level: permissionLevel,
      });
      setSuccess(`Successfully granted ${permissionLevel} access.`);
      setSelectedUserId('');
      fetchPermissions();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to grant permission.');
    } finally {
      setActionLoading(false);
    }
  };

  const handleRevoke = async (permissionId: number) => {
    if (!window.confirm('Are you sure you want to revoke access? The user will immediately lose all access.')) {
      return;
    }

    setActionLoading(true);
    setError(null);
    setSuccess(null);

    try {
      await api.delete(`/documents/${document.id}/permissions/${permissionId}`);
      setSuccess('Permission revoked with immediate effect.');
      fetchPermissions();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to revoke access.');
    } finally {
      setActionLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4">
      <div className="bg-white rounded-xl shadow-xl max-w-lg w-full border border-gray-200 overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-100 flex items-center justify-between">
          <div className="flex items-center space-x-2 text-vault-950 font-bold">
            <ShieldCheck className="w-5 h-5 text-vault-600" />
            <span>Manage Access: {document.title}</span>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 p-1 rounded-md">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-6 space-y-6">
          {error && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700 flex items-start space-x-2">
              <AlertCircle className="w-4 h-4 mt-0.5 flex-shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {success && (
            <div className="p-3 bg-green-50 border border-green-200 rounded-lg text-sm text-green-700">
              {success}
            </div>
          )}

          {/* Grant form */}
          <form onSubmit={handleGrant} className="bg-gray-50 p-4 rounded-lg border border-gray-200 space-y-3">
            <div className="text-xs font-semibold text-gray-700 uppercase tracking-wider flex items-center space-x-1.5">
              <UserPlus className="w-4 h-4 text-vault-600" />
              <span>Grant New Permission</span>
            </div>

            <div className="grid grid-cols-3 gap-3">
              <div className="col-span-2">
                {users.length > 0 ? (
                  <select
                    value={selectedUserId}
                    onChange={(e) => setSelectedUserId(Number(e.target.value))}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-vault-500"
                  >
                    <option value="">Select a user...</option>
                    {users.map((u) => (
                      <option key={u.id} value={u.id}>
                        {u.username} ({u.email})
                      </option>
                    ))}
                  </select>
                ) : (
                  <input
                    type="number"
                    placeholder="Enter Target User ID"
                    value={selectedUserId}
                    onChange={(e) => setSelectedUserId(e.target.value === '' ? '' : Number(e.target.value))}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-vault-500"
                  />
                )}
              </div>

              <div>
                <select
                  value={permissionLevel}
                  onChange={(e) => setPermissionLevel(e.target.value as PermissionLevel)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-vault-500"
                >
                  <option value="READ">READ</option>
                  <option value="EDIT">EDIT</option>
                </select>
              </div>
            </div>

            <button
              type="submit"
              disabled={actionLoading}
              className="w-full py-2 bg-vault-800 text-white rounded-lg text-sm font-medium hover:bg-vault-900 transition-colors disabled:opacity-50"
            >
              {actionLoading ? 'Granting...' : 'Grant Permission'}
            </button>
          </form>

          {/* Current Grants List */}
          <div>
            <div className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
              Current Explicit Grants ({permissions.length})
            </div>

            {loading ? (
              <div className="text-center py-4 text-sm text-gray-400">Loading grants...</div>
            ) : permissions.length === 0 ? (
              <div className="text-center py-4 text-sm text-gray-400 bg-gray-50 rounded-lg border border-dashed border-gray-200">
                This document is private to the owner. No external users have access.
              </div>
            ) : (
              <div className="divide-y divide-gray-100 max-h-56 overflow-y-auto">
                {permissions.map((perm) => (
                  <div key={perm.id} className="py-2.5 flex items-center justify-between">
                    <div>
                      <div className="text-sm font-medium text-gray-900">
                        {perm.user?.username || `User #${perm.user_id}`}
                      </div>
                      <div className="text-xs text-gray-400">
                        Granted on {new Date(perm.created_at).toLocaleDateString()}
                      </div>
                    </div>

                    <div className="flex items-center space-x-3">
                      <span className={`px-2 py-0.5 rounded text-xs font-semibold ${
                        perm.permission_level === 'EDIT'
                          ? 'bg-amber-100 text-amber-800 border border-amber-200'
                          : 'bg-blue-100 text-blue-800 border border-blue-200'
                      }`}>
                        {perm.permission_level}
                      </span>

                      <button
                        onClick={() => handleRevoke(perm.id)}
                        disabled={actionLoading}
                        className="text-gray-400 hover:text-red-600 p-1 rounded transition-colors"
                        title="Revoke Permission Immediately"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
