import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import api from '../services/api';
import { Document, DocumentCategory, AuditEvent } from '../types';
import { 
  ArrowLeft, 
  Download, 
  Share2, 
  Trash2, 
  Edit3, 
  Check, 
  FileText, 
  ShieldCheck, 
  History 
} from 'lucide-react';
import { ShareModal } from '../components/ShareModal';

export const DocumentDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const { user } = useAuth();
  const navigate = useNavigate();

  const [doc, setDoc] = useState<Document | null>(null);
  const [auditEvents, setAuditEvents] = useState<AuditEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Edit state
  const [isEditing, setIsEditing] = useState(false);
  const [editTitle, setEditTitle] = useState('');
  const [editDesc, setEditDesc] = useState('');
  const [editCategory, setEditCategory] = useState<DocumentCategory>('GENERAL');
  const [saving, setSaving] = useState(false);

  const [isShareOpen, setIsShareOpen] = useState(false);

  const fetchDocument = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await api.get<Document>(`/documents/${id}`);
      setDoc(res.data);
      setEditTitle(res.data.title);
      setEditDesc(res.data.description || '');
      setEditCategory(res.data.category);

      // Fetch audit activity if allowed
      try {
        const auditRes = await api.get<AuditEvent[]>(`/audit/documents/${id}`);
        setAuditEvents(auditRes.data);
      } catch {
        // Normal if viewer is not owner or admin
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load document or access denied.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDocument();
  }, [id]);

  const handleDownload = async () => {
    if (!doc) return;
    try {
      const res = await api.get(`/documents/${doc.id}/download`, { responseType: 'blob' });
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const link = window.document.createElement('a');
      link.href = url;
      link.setAttribute('download', doc.file_name);
      window.document.body.appendChild(link);
      link.click();
      link.remove();
    } catch {
      alert('Download access denied. Your permissions may have been updated.');
    }
  };

  const handleUpdate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!doc) return;
    setSaving(true);
    try {
      const res = await api.patch<Document>(`/documents/${doc.id}`, {
        title: editTitle,
        description: editDesc,
        category: editCategory,
      });
      setDoc(res.data);
      setIsEditing(false);
      fetchDocument();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to update document.');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!doc) return;
    if (!window.confirm(`Are you sure you want to permanently delete "${doc.title}"?`)) return;
    try {
      await api.delete(`/documents/${doc.id}`);
      navigate('/documents');
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Delete failed.');
    }
  };

  if (loading) {
    return <div className="text-center py-20 text-sm text-gray-500">Loading document details...</div>;
  }

  if (error || !doc) {
    return (
      <div className="bg-white p-8 rounded-xl border border-red-200 text-center space-y-4">
        <div className="text-red-600 font-semibold">{error || 'Document not found.'}</div>
        <Link to="/documents" className="text-sm text-vault-600 hover:underline">
          Return to Document Library
        </Link>
      </div>
    );
  }

  const isOwner = doc.owner_id === user?.id;

  return (
    <div className="space-y-6">
      {/* Back button */}
      <div>
        <Link
          to="/documents"
          className="inline-flex items-center space-x-1.5 text-xs font-semibold text-gray-500 hover:text-gray-900 transition-colors"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>Back to Documents</span>
        </Link>
      </div>

      {/* Main Header Card */}
      <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-start space-x-4">
          <div className="p-3 bg-vault-50 text-vault-600 rounded-xl">
            <FileText className="w-8 h-8" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-vault-950">{doc.title}</h1>
            <p className="text-sm text-gray-500 mt-1">{doc.description || 'No description provided.'}</p>
            <div className="flex flex-wrap items-center gap-3 mt-3">
              <span className="px-2.5 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-700">
                {doc.category}
              </span>
              <span className="text-xs text-gray-400">
                {(doc.file_size / 1024).toFixed(1)} KB • {doc.mime_type}
              </span>
              <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${
                isOwner ? 'bg-blue-50 text-blue-700 border border-blue-200' : 'bg-gray-100 text-gray-600'
              }`}>
                {isOwner ? 'Owner' : 'Shared Document'}
              </span>
            </div>
          </div>
        </div>

        <div className="flex items-center space-x-3">
          <button
            onClick={handleDownload}
            className="px-4 py-2 bg-vault-900 text-white rounded-lg text-sm font-semibold hover:bg-vault-800 transition-colors flex items-center space-x-2"
          >
            <Download className="w-4 h-4" />
            <span>Download</span>
          </button>

          {isOwner && (
            <>
              <button
                onClick={() => setIsShareOpen(true)}
                className="px-3.5 py-2 border border-gray-300 rounded-lg text-sm font-semibold text-gray-700 hover:bg-gray-50 transition-colors flex items-center space-x-2"
              >
                <Share2 className="w-4 h-4" />
                <span>Share</span>
              </button>

              <button
                onClick={handleDelete}
                className="p-2 border border-red-200 rounded-lg text-red-600 hover:bg-red-50 transition-colors"
                title="Delete Document"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </>
          )}
        </div>
      </div>

      {/* Grid: Metadata Details & Edit Form */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          {/* Edit Form Card */}
          <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-base font-bold text-vault-950">Document Information</h2>
              <button
                onClick={() => setIsEditing(!isEditing)}
                className="text-xs font-semibold text-vault-600 hover:text-vault-700 flex items-center space-x-1"
              >
                <Edit3 className="w-3.5 h-3.5" />
                <span>{isEditing ? 'Cancel Editing' : 'Edit Metadata'}</span>
              </button>
            </div>

            {isEditing ? (
              <form onSubmit={handleUpdate} className="space-y-4">
                <div>
                  <label className="block text-xs font-semibold uppercase text-gray-700 mb-1">Title</label>
                  <input
                    type="text"
                    required
                    value={editTitle}
                    onChange={(e) => setEditTitle(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-vault-500"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold uppercase text-gray-700 mb-1">Category</label>
                  <select
                    value={editCategory}
                    onChange={(e) => setEditCategory(e.target.value as DocumentCategory)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-vault-500"
                  >
                    <option value="GENERAL">General</option>
                    <option value="FINANCIAL">Financial</option>
                    <option value="LEGAL">Legal</option>
                    <option value="HR">HR</option>
                    <option value="TECHNICAL">Technical</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold uppercase text-gray-700 mb-1">Description</label>
                  <textarea
                    rows={3}
                    value={editDesc}
                    onChange={(e) => setEditDesc(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-vault-500"
                  />
                </div>

                <div className="flex justify-end space-x-2 pt-2">
                  <button
                    type="submit"
                    disabled={saving}
                    className="px-4 py-2 bg-vault-900 text-white rounded-lg text-sm font-semibold hover:bg-vault-800 disabled:opacity-50 flex items-center space-x-2"
                  >
                    <Check className="w-4 h-4" />
                    <span>{saving ? 'Saving...' : 'Save Changes'}</span>
                  </button>
                </div>
              </form>
            ) : (
              <dl className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-sm">
                <div>
                  <dt className="text-xs text-gray-400 uppercase font-semibold">Original Filename</dt>
                  <dd className="font-medium text-gray-900 mt-0.5">{doc.file_name}</dd>
                </div>
                <div>
                  <dt className="text-xs text-gray-400 uppercase font-semibold">Classification</dt>
                  <dd className="font-medium text-gray-900 mt-0.5">{doc.category}</dd>
                </div>
                <div>
                  <dt className="text-xs text-gray-400 uppercase font-semibold">Date Uploaded</dt>
                  <dd className="font-medium text-gray-900 mt-0.5">{new Date(doc.created_at).toLocaleString()}</dd>
                </div>
                <div>
                  <dt className="text-xs text-gray-400 uppercase font-semibold">Last Modified</dt>
                  <dd className="font-medium text-gray-900 mt-0.5">{new Date(doc.updated_at).toLocaleString()}</dd>
                </div>
              </dl>
            )}
          </div>

          {/* Document Audit Activity */}
          {(isOwner || user?.role === 'ADMIN') && (
            <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm">
              <div className="flex items-center space-x-2 mb-4">
                <History className="w-5 h-5 text-vault-600" />
                <h2 className="text-base font-bold text-vault-950">Document Access Audit Log</h2>
              </div>

              {auditEvents.length === 0 ? (
                <div className="text-center py-6 text-sm text-gray-400">
                  No audit records logged for this document yet.
                </div>
              ) : (
                <div className="divide-y divide-gray-100">
                  {auditEvents.map((ev) => (
                    <div key={ev.id} className="py-2.5 flex items-center justify-between text-xs">
                      <div>
                        <span className="font-semibold text-gray-900">{ev.action}</span>
                        <span className="text-gray-400 ml-2">by User #{ev.actor_id || 'System'}</span>
                      </div>
                      <div className="flex items-center space-x-3">
                        <span className={`px-2 py-0.5 rounded font-bold ${
                          ev.result === 'SUCCESS' ? 'text-green-700 bg-green-50' : 'text-red-700 bg-red-50'
                        }`}>
                          {ev.result}
                        </span>
                        <span className="text-gray-400">{new Date(ev.timestamp).toLocaleTimeString()}</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Security & Access Policies Sidebar */}
        <div className="space-y-6">
          <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm space-y-4">
            <div className="flex items-center space-x-2 text-vault-950 font-bold">
              <ShieldCheck className="w-5 h-5 text-vault-600" />
              <span>Zero-Trust Verification</span>
            </div>
            <p className="text-xs text-gray-600 leading-relaxed">
              Access to this document is verified on each request against live database permissions. 
              No persistent authorization tokens are issued for document content.
            </p>
            <div className="pt-2 border-t border-gray-100 text-xs text-gray-500 space-y-2">
              <div className="flex items-center justify-between">
                <span>Storage Key:</span>
                <span className="font-mono text-gray-700">UUID Private Isolation</span>
              </div>
              <div className="flex items-center justify-between">
                <span>Magic Bytes Verified:</span>
                <span className="text-green-600 font-semibold">Active</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {isOwner && (
        <ShareModal
          document={doc}
          isOpen={isShareOpen}
          onClose={() => setIsShareOpen(false)}
        />
      )}
    </div>
  );
};
