import React, { useState, useEffect } from 'react';
import api from '../services/api';
import { AuditEvent } from '../types';
import { 
  ShieldCheck, 
  ShieldAlert, 
  Download, 
  CheckCircle, 
  XCircle, 
  RefreshCw, 
  Filter 
} from 'lucide-react';

export const AuditPage: React.FC = () => {
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [verifyStatus, setVerifyStatus] = useState<{
    valid?: boolean;
    message?: string;
    total_events?: number;
    tampered_event_id?: number;
  } | null>(null);
  const [verifying, setVerifying] = useState(false);

  // Filters
  const [actionFilter, setActionFilter] = useState('');
  const [resultFilter, setResultFilter] = useState('');

  const fetchAuditLogs = async () => {
    try {
      setLoading(true);
      const params: any = {};
      if (actionFilter) params.action = actionFilter;
      if (resultFilter) params.result = resultFilter;

      const res = await api.get<AuditEvent[]>('/audit', { params });
      setEvents(res.data);
    } catch (err) {
      console.error('Failed to load audit logs', err);
    } finally {
      setLoading(false);
    }
  };

  const handleVerifyChain = async () => {
    try {
      setVerifying(true);
      const res = await api.get('/audit/verify');
      setVerifyStatus(res.data);
    } catch (err: any) {
      alert('Verification failed to execute.');
    } finally {
      setVerifying(false);
    }
  };

  const handleExportCSV = async () => {
    try {
      const res = await api.get('/admin/reports/export', { responseType: 'blob' });
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', 'trustvault_compliance_audit_log.csv');
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch {
      alert('Export failed.');
    }
  };

  useEffect(() => {
    fetchAuditLogs();
    handleVerifyChain();
  }, [actionFilter, resultFilter]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-vault-950 tracking-tight">Compliance & Audit Trail</h1>
          <p className="text-sm text-gray-500">
            Immutable SHA-256 cryptographic hash-linked activity ledger
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <button
            onClick={handleVerifyChain}
            disabled={verifying}
            className="px-3.5 py-2 border border-gray-300 rounded-lg text-sm font-semibold text-gray-700 hover:bg-gray-50 transition-colors flex items-center space-x-2"
          >
            <RefreshCw className={`w-4 h-4 ${verifying ? 'animate-spin' : ''}`} />
            <span>Verify Integrity</span>
          </button>

          <button
            onClick={handleExportCSV}
            className="px-3.5 py-2 bg-vault-900 text-white rounded-lg text-sm font-semibold hover:bg-vault-800 transition-colors flex items-center space-x-2"
          >
            <Download className="w-4 h-4" />
            <span>Export CSV</span>
          </button>
        </div>
      </div>

      {/* Verification Status Banner */}
      {verifyStatus && (
        <div className={`p-4 rounded-xl border flex items-center justify-between ${
          verifyStatus.valid
            ? 'bg-emerald-50 border-emerald-200 text-emerald-900'
            : 'bg-red-50 border-red-200 text-red-900'
        }`}>
          <div className="flex items-center space-x-3">
            {verifyStatus.valid ? (
              <ShieldCheck className="w-6 h-6 text-emerald-600 flex-shrink-0" />
            ) : (
              <ShieldAlert className="w-6 h-6 text-red-600 flex-shrink-0" />
            )}
            <div>
              <div className="font-bold text-sm">
                {verifyStatus.valid
                  ? 'Cryptographic Hash-Chain Intact & Untampered'
                  : 'TAMPERING DETECTED IN AUDIT LEDGER'}
              </div>
              <div className="text-xs opacity-90 mt-0.5">
                {verifyStatus.message} • {verifyStatus.total_events} verified blocks
              </div>
            </div>
          </div>
          <span className="text-xs font-mono font-bold uppercase tracking-wider px-2.5 py-1 rounded bg-white/70">
            SHA-256 Validated
          </span>
        </div>
      )}

      {/* Filter Bar */}
      <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm flex flex-wrap gap-4 items-center">
        <div className="flex items-center space-x-2 text-xs font-semibold text-gray-500 uppercase">
          <Filter className="w-4 h-4" />
          <span>Filters:</span>
        </div>

        <select
          value={actionFilter}
          onChange={(e) => setActionFilter(e.target.value)}
          className="px-3 py-1.5 border border-gray-300 rounded-lg text-xs bg-white focus:outline-none focus:ring-2 focus:ring-vault-500"
        >
          <option value="">All Actions</option>
          <option value="USER_LOGIN_SUCCESS">Login Success</option>
          <option value="USER_LOGIN_FAILED">Login Failed</option>
          <option value="DOCUMENT_UPLOAD">Document Upload</option>
          <option value="DOCUMENT_READ">Document Read</option>
          <option value="DOCUMENT_DOWNLOAD">Document Download</option>
          <option value="PERMISSION_GRANT">Permission Grant</option>
          <option value="PERMISSION_REVOKE">Permission Revoke</option>
          <option value="UNAUTHORIZED_ACCESS_ATTEMPT">Denied Attempt</option>
        </select>

        <select
          value={resultFilter}
          onChange={(e) => setResultFilter(e.target.value)}
          className="px-3 py-1.5 border border-gray-300 rounded-lg text-xs bg-white focus:outline-none focus:ring-2 focus:ring-vault-500"
        >
          <option value="">All Results</option>
          <option value="SUCCESS">Success Only</option>
          <option value="DENIED">Denied / Unauthorized Only</option>
        </select>
      </div>

      {/* Audit Log Table */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
        {loading ? (
          <div className="p-12 text-center text-sm text-gray-400">Loading audit records...</div>
        ) : events.length === 0 ? (
          <div className="p-12 text-center text-sm text-gray-400">No audit events match filters.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-gray-50 text-gray-500 font-semibold uppercase tracking-wider">
                <tr>
                  <th className="px-5 py-3">ID</th>
                  <th className="px-5 py-3">Timestamp</th>
                  <th className="px-5 py-3">Actor</th>
                  <th className="px-5 py-3">Doc ID</th>
                  <th className="px-5 py-3">Action</th>
                  <th className="px-5 py-3">Result</th>
                  <th className="px-5 py-3">SHA-256 Hash</th>
                  <th className="px-5 py-3">Details</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 font-mono">
                {events.map((ev) => (
                  <tr key={ev.id} className="hover:bg-gray-50/75 transition-colors">
                    <td className="px-5 py-3 text-gray-500">#{ev.id}</td>
                    <td className="px-5 py-3 text-gray-700 whitespace-nowrap">
                      {new Date(ev.timestamp).toLocaleString()}
                    </td>
                    <td className="px-5 py-3 font-sans">
                      {ev.actor ? (
                        <span className="font-medium text-vault-950">{ev.actor.username}</span>
                      ) : (
                        <span className="text-gray-400">User #{ev.actor_id || 'System'}</span>
                      )}
                    </td>
                    <td className="px-5 py-3 text-gray-500">
                      {ev.document_id ? `#${ev.document_id}` : '-'}
                    </td>
                    <td className="px-5 py-3 font-sans font-medium text-gray-800">
                      {ev.action}
                    </td>
                    <td className="px-5 py-3 font-sans">
                      <span className={`inline-flex items-center space-x-1 px-2 py-0.5 rounded font-bold ${
                        ev.result === 'SUCCESS' ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'
                      }`}>
                        {ev.result === 'SUCCESS' ? (
                          <CheckCircle className="w-3 h-3" />
                        ) : (
                          <XCircle className="w-3 h-3" />
                        )}
                        <span>{ev.result}</span>
                      </span>
                    </td>
                    <td className="px-5 py-3 text-gray-400 text-[10px]" title={ev.current_hash}>
                      {ev.current_hash.substring(0, 12)}...{ev.current_hash.substring(56)}
                    </td>
                    <td className="px-5 py-3 text-gray-500 max-w-xs truncate font-sans text-xs" title={ev.details || ''}>
                      {ev.details || '-'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
