import React, { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import api from '../services/api';
import { Document } from '../types';
import { Files, UploadCloud, Users, ShieldAlert, ArrowRight, FileText, Download } from 'lucide-react';
import { Link } from 'react-router-dom';
import { UploadModal } from '../components/UploadModal';

export const DashboardPage: React.FC = () => {
  const { user } = useAuth();
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);
  const [isUploadOpen, setIsUploadOpen] = useState(false);

  const fetchDocuments = async () => {
    try {
      setLoading(true);
      const res = await api.get<Document[]>('/documents');
      setDocuments(res.data);
    } catch (err) {
      console.error('Failed to load documents', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDocuments();
  }, []);

  const ownedDocs = documents.filter((d) => d.owner_id === user?.id);
  const sharedDocs = documents.filter((d) => d.owner_id !== user?.id);

  const handleDownload = async (docId: number, fileName: string) => {
    try {
      const res = await api.get(`/documents/${docId}/download`, { responseType: 'blob' });
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const link = window.document.createElement('a');
      link.href = url;
      link.setAttribute('download', fileName);
      window.document.body.appendChild(link);
      link.click();
      link.remove();
    } catch {
      alert('Download failed. You may not have permission to download this document.');
    }
  };

  return (
    <div className="space-y-8">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-vault-950 tracking-tight">Security Dashboard</h1>
          <p className="text-sm text-gray-500">
            Welcome back, <span className="font-semibold text-gray-700">{user?.full_name || user?.username}</span>. Your workspace is secured with live zero-trust enforcement.
          </p>
        </div>

        {user?.role !== 'VIEWER' && (
          <button
            onClick={() => setIsUploadOpen(true)}
            className="inline-flex items-center space-x-2 px-4 py-2.5 bg-vault-900 text-white rounded-lg text-sm font-semibold hover:bg-vault-800 shadow-sm transition-colors"
          >
            <UploadCloud className="w-4 h-4" />
            <span>Upload Document</span>
          </button>
        )}
      </div>

      {/* Metrics Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-gray-500">Accessible Docs</span>
            <div className="p-2 bg-blue-50 text-blue-700 rounded-lg">
              <Files className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-4">
            <span className="text-3xl font-extrabold text-vault-950">{documents.length}</span>
            <span className="ml-2 text-xs text-gray-400">total permitted</span>
          </div>
        </div>

        <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-gray-500">Owned by You</span>
            <div className="p-2 bg-emerald-50 text-emerald-700 rounded-lg">
              <UploadCloud className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-4">
            <span className="text-3xl font-extrabold text-vault-950">{ownedDocs.length}</span>
            <span className="ml-2 text-xs text-gray-400">your uploads</span>
          </div>
        </div>

        <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-gray-500">Shared With You</span>
            <div className="p-2 bg-amber-50 text-amber-700 rounded-lg">
              <Users className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-4">
            <span className="text-3xl font-extrabold text-vault-950">{sharedDocs.length}</span>
            <span className="ml-2 text-xs text-gray-400">explicit grants</span>
          </div>
        </div>

        <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-gray-500">Access Mode</span>
            <div className="p-2 bg-purple-50 text-purple-700 rounded-lg">
              <ShieldAlert className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-4">
            <span className="text-xl font-bold text-vault-950">{user?.role}</span>
            <span className="block text-xs text-gray-400 mt-1">Live DB Checked</span>
          </div>
        </div>
      </div>

      {/* Recent Documents Table */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-100 flex items-center justify-between">
          <div>
            <h2 className="text-base font-bold text-vault-950">Recent Authorized Documents</h2>
            <p className="text-xs text-gray-500">Documents you are actively permitted to view</p>
          </div>
          <Link
            to="/documents"
            className="text-xs font-semibold text-vault-600 hover:text-vault-700 flex items-center space-x-1"
          >
            <span>View All</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>

        {loading ? (
          <div className="p-8 text-center text-sm text-gray-400">Loading documents...</div>
        ) : documents.length === 0 ? (
          <div className="p-12 text-center">
            <FileText className="w-10 h-10 text-gray-300 mx-auto mb-3" />
            <h3 className="text-sm font-semibold text-gray-900">No documents found</h3>
            <p className="text-xs text-gray-500 mt-1 max-w-sm mx-auto">
              You haven't uploaded or been granted access to any documents yet.
            </p>
            {user?.role !== 'VIEWER' && (
              <button
                onClick={() => setIsUploadOpen(true)}
                className="mt-4 px-3 py-1.5 bg-vault-900 text-white rounded-lg text-xs font-medium hover:bg-vault-800"
              >
                Upload Document
              </button>
            )}
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-gray-50 text-gray-500 text-xs font-semibold uppercase tracking-wider">
                <tr>
                  <th className="px-6 py-3">Document Title</th>
                  <th className="px-6 py-3">Category</th>
                  <th className="px-6 py-3">File Size</th>
                  <th className="px-6 py-3">Ownership</th>
                  <th className="px-6 py-3">Uploaded</th>
                  <th className="px-6 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {documents.slice(0, 5).map((doc) => {
                  const isOwner = doc.owner_id === user?.id;
                  return (
                    <tr key={doc.id} className="hover:bg-gray-50/75 transition-colors">
                      <td className="px-6 py-3.5 font-medium text-vault-950 flex items-center space-x-2">
                        <FileText className="w-4 h-4 text-vault-600 flex-shrink-0" />
                        <Link to={`/documents/${doc.id}`} className="hover:underline">
                          {doc.title}
                        </Link>
                      </td>
                      <td className="px-6 py-3.5">
                        <span className="px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-700">
                          {doc.category}
                        </span>
                      </td>
                      <td className="px-6 py-3.5 text-xs text-gray-500">
                        {(doc.file_size / 1024).toFixed(1)} KB
                      </td>
                      <td className="px-6 py-3.5">
                        <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${
                          isOwner ? 'bg-blue-50 text-blue-700 border border-blue-200' : 'bg-gray-100 text-gray-600'
                        }`}>
                          {isOwner ? 'Owned' : 'Shared'}
                        </span>
                      </td>
                      <td className="px-6 py-3.5 text-xs text-gray-500">
                        {new Date(doc.created_at).toLocaleDateString()}
                      </td>
                      <td className="px-6 py-3.5 text-right">
                        <button
                          onClick={() => handleDownload(doc.id, doc.file_name)}
                          className="p-1.5 text-gray-400 hover:text-vault-600 rounded transition-colors"
                          title="Download Document"
                        >
                          <Download className="w-4 h-4" />
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

      <UploadModal
        isOpen={isUploadOpen}
        onClose={() => setIsUploadOpen(false)}
        onUploaded={(newDoc) => {
          setDocuments([newDoc, ...documents]);
        }}
      />
    </div>
  );
};
