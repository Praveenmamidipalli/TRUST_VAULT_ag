import React, { useState } from 'react';
import { X, Upload, FileText, AlertCircle } from 'lucide-react';
import api from '../services/api';
import { Document, DocumentCategory } from '../types';

interface UploadModalProps {
  isOpen: boolean;
  onClose: () => void;
  onUploaded: (doc: Document) => void;
}

export const UploadModal: React.FC<UploadModalProps> = ({ isOpen, onClose, onUploaded }) => {
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [category, setCategory] = useState<DocumentCategory>('GENERAL');
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) {
      setError('Please select a document file to upload.');
      return;
    }

    setLoading(true);
    setError(null);

    const formData = new FormData();
    formData.append('title', title);
    if (description) formData.append('description', description);
    formData.append('category', category);
    formData.append('file', file);

    try {
      const res = await api.post<Document>('/documents', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      onUploaded(res.data);
      onClose();
      setTitle('');
      setDescription('');
      setCategory('GENERAL');
      setFile(null);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to upload document. Please check file format and size.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4">
      <div className="bg-white rounded-xl shadow-xl max-w-lg w-full border border-gray-200 overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-100 flex items-center justify-between">
          <div className="flex items-center space-x-2 text-vault-950 font-bold">
            <Upload className="w-5 h-5 text-vault-600" />
            <span>Upload Secure Document</span>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 p-1 rounded-md">
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {error && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700 flex items-start space-x-2">
              <AlertCircle className="w-4 h-4 mt-0.5 flex-shrink-0" />
              <span>{error}</span>
            </div>
          )}

          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-gray-700 mb-1">
              Document Title *
            </label>
            <input
              type="text"
              required
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. Master Services Agreement 2026"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-vault-500 focus:outline-none"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-gray-700 mb-1">
              Category
            </label>
            <select
              value={category}
              onChange={(e) => setCategory(e.target.value as DocumentCategory)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-vault-500 focus:outline-none"
            >
              <option value="GENERAL">General</option>
              <option value="FINANCIAL">Financial</option>
              <option value="LEGAL">Legal</option>
              <option value="HR">HR</option>
              <option value="TECHNICAL">Technical</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-gray-700 mb-1">
              Description (Optional)
            </label>
            <textarea
              rows={2}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Brief context or sensitivity notes..."
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-vault-500 focus:outline-none"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-gray-700 mb-1">
              Document File (PDF, DOCX, TXT, PNG) *
            </label>
            <div className="border-2 border-dashed border-gray-300 rounded-lg p-4 text-center hover:border-vault-500 transition-colors">
              <input
                type="file"
                required
                accept=".pdf,.docx,.txt,.png,.jpg,.jpeg"
                onChange={(e) => setFile(e.target.files ? e.target.files[0] : null)}
                className="hidden"
                id="file-upload"
              />
              <label htmlFor="file-upload" className="cursor-pointer flex flex-col items-center space-y-1">
                <FileText className="w-8 h-8 text-vault-500" />
                <span className="text-sm font-medium text-vault-700">
                  {file ? file.name : 'Click to select file from your device'}
                </span>
                <span className="text-xs text-gray-400">Max size: 50MB</span>
              </label>
            </div>
          </div>

          <div className="pt-2 flex justify-end space-x-3">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 border border-gray-300 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="px-4 py-2 bg-vault-900 text-white rounded-lg text-sm font-medium hover:bg-vault-800 disabled:opacity-50 flex items-center space-x-2"
            >
              {loading && <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>}
              <span>Upload Document</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
