import React, { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import api from '../services/api';
import { Document } from '../types';
import { 
  Search, 
  UploadCloud, 
  FileText, 
  Download, 
  Share2, 
  Trash2, 
  Eye, 
  Filter
} from 'lucide-react';
import { Link } from 'react-router-dom';
import { UploadModal } from '../components/UploadModal';
import { ShareModal } from '../components/ShareModal';

export const DocumentsPage: React.FC = () => {
  const { user } = useAuth();
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [categoryFilter, setCategoryFilter] = useState<string>('ALL');
  const [ownershipFilter, setOwnershipFilter] = useState<'ALL' | 'OWNED' | 'SHARED'>('ALL');
  
  const [isUploadOpen, setIsUploadOpen] = useState(false);
  const [selectedDocForShare, setSelectedDocForShare] = useState<Document | null>(null);

  const fetchDocuments = async () => {
    try {
      setLoading(true);
      const params: any = {};
      if (search) params.q = search;
      if (categoryFilter !== 'ALL') params.category = categoryFilter;

      const res = await api.get<Document[]>('/documents', { params });
      setDocuments(res.data);
    } catch (err) {
      console.error('Failed to load documents', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const delayDebounce = setTimeout(() => {
      fetchDocuments();
    }, 250);
    return () => clearTimeout(delayDebounce);
  }, [search, categoryFilter]);

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
      alert('Download access denied. Your permission may have been revoked.');
    }
  };

  const handleDelete = async (docId: number, title: string) => {
    if (!window.confirm(`Are you sure you want to delete "${title}"? This action cannot be undone.`)) {
      return;
    }
    try {
      await api.delete(`/documents/${docId}`);
      setDocuments(documents.filter((d) => d.id !== docId));
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Delete failed.');
    }
  };

  const filteredDocuments = documents.filter((doc) => {
    if (ownershipFilter === 'OWNED') return doc.owner_id === user?.id;
    if (ownershipFilter === 'SHARED') return doc.owner_id !== user?.id;
    return true;
  });

  return (
    <div className="space-y-6">
      {/* Page Title & Actions */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-vault-950 tracking-tight">Document Library</h1>
          <p className="text-sm text-gray-500">
            Secure, end-to-end access-controlled enterprise document repository
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

      {/* Search & Filter Toolbar */}
      <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm flex flex-col md:flex-row gap-4 items-center justify-between">
        <div className="relative w-full md:w-96">
          <Search className="w-4 h-4 absolute left-3 top-3 text-gray-400" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search documents by title or description..."
            className="w-full pl-9 pr-4 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-vault-500"
          />
        </div>

        <div className="flex flex-wrap items-center gap-3 w-full md:w-auto">
          {/* Category Dropdown */}
          <div className="flex items-center space-x-2">
            <Filter className="w-4 h-4 text-gray-400" />
            <select
              value={categoryFilter}
              onChange={(e) => setCategoryFilter(e.target.value)}
              className="px-3 py-2 border border-gray-300 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-vault-500"
            >
              <option value="ALL">All Categories</option>
              <option value="GENERAL">General</option>
              <option value="FINANCIAL">Financial</option>
              <option value="LEGAL">Legal</option>
              <option value="HR">HR</option>
              <option value="TECHNICAL">Technical</option>
            </select>
          </div>

          {/* Ownership Filter */}
          <div className="flex rounded-lg border border-gray-200 p-0.5 bg-gray-50 text-xs font-medium">
            <button
              onClick={() => setOwnershipFilter('ALL')}
              className={`px-3 py-1.5 rounded-md transition-colors ${ownershipFilter === 'ALL' ? 'bg-white shadow-sm font-bold text-vault-950' : 'text-gray-600'}`}
            >
              All
            </button>
            <button
              onClick={() => setOwnershipFilter('OWNED')}
              className={`px-3 py-1.5 rounded-md transition-colors ${ownershipFilter === 'OWNED' ? 'bg-white shadow-sm font-bold text-vault-950' : 'text-gray-600'}`}
            >
              Owned
            </button>
            <button
              onClick={() => setOwnershipFilter('SHARED')}
              className={`px-3 py-1.5 rounded-md transition-colors ${ownershipFilter === 'SHARED' ? 'bg-white shadow-sm font-bold text-vault-950' : 'text-gray-600'}`}
            >
              Shared
            </button>
          </div>
        </div>
      </div>

      {/* Documents Table */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
        {loading ? (
          <div className="p-12 text-center text-sm text-gray-400">Loading documents...</div>
        ) : filteredDocuments.length === 0 ? (
          <div className="p-16 text-center">
            <FileText className="w-12 h-12 text-gray-300 mx-auto mb-3" />
            <h3 className="text-base font-semibold text-gray-900">No matching documents found</h3>
            <p className="text-sm text-gray-500 mt-1 max-w-sm mx-auto">
              Try adjusting your search terms or filters.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-gray-50 text-gray-500 text-xs font-semibold uppercase tracking-wider">
                <tr>
                  <th className="px-6 py-3.5">Title & Filename</th>
                  <th className="px-6 py-3.5">Category</th>
                  <th className="px-6 py-3.5">Size</th>
                  <th className="px-6 py-3.5">Access Type</th>
                  <th className="px-6 py-3.5">Date Added</th>
                  <th className="px-6 py-3.5 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {filteredDocuments.map((doc) => {
                  const isOwner = doc.owner_id === user?.id;
                  return (
                    <tr key={doc.id} className="hover:bg-gray-50/75 transition-colors">
                      <td className="px-6 py-4">
                        <div className="flex items-start space-x-3">
                          <FileText className="w-5 h-5 text-vault-600 flex-shrink-0 mt-0.5" />
                          <div>
                            <Link to={`/documents/${doc.id}`} className="font-semibold text-vault-950 hover:underline">
                              {doc.title}
                            </Link>
                            <div className="text-xs text-gray-400">{doc.file_name}</div>
                          </div>
                        </div>
                      </td>

                      <td className="px-6 py-4">
                        <span className="px-2.5 py-1 rounded text-xs font-medium bg-gray-100 text-gray-700">
                          {doc.category}
                        </span>
                      </td>

                      <td className="px-6 py-4 text-xs text-gray-500">
                        {(doc.file_size / 1024).toFixed(1)} KB
                      </td>

                      <td className="px-6 py-4">
                        <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${
                          isOwner ? 'bg-blue-50 text-blue-700 border border-blue-200' : 'bg-gray-100 text-gray-600'
                        }`}>
                          {isOwner ? 'Owner' : 'Shared With You'}
                        </span>
                      </td>

                      <td className="px-6 py-4 text-xs text-gray-500">
                        {new Date(doc.created_at).toLocaleDateString()}
                      </td>

                      <td className="px-6 py-4 text-right">
                        <div className="flex items-center justify-end space-x-2">
                          <Link
                            to={`/documents/${doc.id}`}
                            className="p-1.5 text-gray-400 hover:text-vault-600 rounded transition-colors"
                            title="View Details"
                          >
                            <Eye className="w-4 h-4" />
                          </Link>

                          <button
                            onClick={() => handleDownload(doc.id, doc.file_name)}
                            className="p-1.5 text-gray-400 hover:text-vault-600 rounded transition-colors"
                            title="Download Document"
                          >
                            <Download className="w-4 h-4" />
                          </button>

                          {isOwner && (
                            <>
                              <button
                                onClick={() => setSelectedDocForShare(doc)}
                                className="p-1.5 text-gray-400 hover:text-vault-600 rounded transition-colors"
                                title="Share & Permissions"
                              >
                                <Share2 className="w-4 h-4" />
                              </button>

                              <button
                                onClick={() => handleDelete(doc.id, doc.title)}
                                className="p-1.5 text-gray-400 hover:text-red-600 rounded transition-colors"
                                title="Delete Document"
                              >
                                <Trash2 className="w-4 h-4" />
                              </button>
                            </>
                          )}
                        </div>
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

      {selectedDocForShare && (
        <ShareModal
          document={selectedDocForShare}
          isOpen={!!selectedDocForShare}
          onClose={() => setSelectedDocForShare(null)}
        />
      )}
    </div>
  );
};
