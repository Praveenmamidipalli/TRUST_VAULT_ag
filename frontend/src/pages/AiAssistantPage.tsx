import React, { useState } from 'react';
import api from '../services/api';
import { Bot, Sparkles, Send, FileText, ShieldCheck, AlertCircle } from 'lucide-react';

interface AiQueryResponse {
  answer: string;
  cited_documents: Array<{
    document_id: number;
    title: string;
    similarity_score: number;
    chunk_preview: string;
  }>;
  insufficient_evidence: boolean;
  authorized_docs_searched: number;
}

export const AiAssistantPage: React.FC = () => {
  const [question, setQuestion] = useState('');
  const [loading, setLoading] = useState(false);
  const [response, setResponse] = useState<AiQueryResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleAsk = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!question.trim()) return;

    setLoading(true);
    setError(null);

    try {
      const res = await api.post<AiQueryResponse>('/ai/ask', {
        question: question,
      });
      setResponse(res.data);
    } catch (err: any) {
      setError(
        err.response?.data?.detail ||
        'AI intelligence service unavailable or no accessible documents match your query.'
      );
    } finally {
      setLoading(false);
    }
  };

  const handlePredefined = (prompt: string) => {
    setQuestion(prompt);
  };

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      {/* Header */}
      <div>
        <div className="flex items-center space-x-2 text-vault-600 mb-1">
          <Sparkles className="w-5 h-5" />
          <span className="text-xs font-bold uppercase tracking-wider">Document Intelligence</span>
        </div>
        <h1 className="text-2xl font-bold text-vault-950 tracking-tight">Permission-Aware AI Assistant</h1>
        <p className="text-sm text-gray-500 mt-1">
          Ask questions across your permitted document corpus. Security guarantee: The LLM is strictly isolated and never ingests unauthorized chunks.
        </p>
      </div>

      {/* Security Banner */}
      <div className="p-4 bg-vault-50 border border-vault-100 rounded-xl flex items-start space-x-3 text-xs text-vault-900">
        <ShieldCheck className="w-5 h-5 text-vault-600 mt-0.5 flex-shrink-0" />
        <div>
          <span className="font-bold">Zero-Trust Grounding: </span>
          <span>
            Retrieval-Augmented Generation (RAG) restricts search to active document IDs granted to your account in the live database. No unauthorized confidential metadata reaches the model context.
          </span>
        </div>
      </div>

      {/* Suggested Prompts */}
      <div className="flex flex-wrap gap-2 text-xs">
        <span className="text-gray-400 font-medium py-1">Try asking:</span>
        <button
          onClick={() => handlePredefined('What are the payment terms and revenue figures?')}
          className="px-3 py-1 bg-white border border-gray-200 rounded-full hover:border-vault-500 text-gray-700 transition-colors"
        >
          Payment terms & revenue
        </button>
        <button
          onClick={() => handlePredefined('What is the executive equity vesting schedule?')}
          className="px-3 py-1 bg-white border border-gray-200 rounded-full hover:border-vault-500 text-gray-700 transition-colors"
        >
          Equity vesting schedule
        </button>
        <button
          onClick={() => handlePredefined('What are the mutual non-disclosure and trade secret obligations?')}
          className="px-3 py-1 bg-white border border-gray-200 rounded-full hover:border-vault-500 text-gray-700 transition-colors"
        >
          Confidentiality & trade secrets
        </button>
      </div>

      {/* Query Form */}
      <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm">
        <form onSubmit={handleAsk} className="flex gap-3">
          <input
            type="text"
            required
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="Ask a question about your accessible documents..."
            className="flex-1 px-4 py-2.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-vault-500"
          />
          <button
            type="submit"
            disabled={loading}
            className="px-5 py-2.5 bg-vault-900 text-white rounded-lg text-sm font-semibold hover:bg-vault-800 disabled:opacity-50 transition-colors flex items-center space-x-2"
          >
            {loading ? (
              <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
            ) : (
              <Send className="w-4 h-4" />
            )}
            <span>Analyze</span>
          </button>
        </form>
      </div>

      {/* Error state */}
      {error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-xl text-sm text-red-700 flex items-start space-x-2">
          <AlertCircle className="w-4 h-4 mt-0.5 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* AI Answer & Grounded Citations */}
      {response && (
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden space-y-6 p-6">
          <div className="flex items-center justify-between border-b border-gray-100 pb-4">
            <div className="flex items-center space-x-2 text-vault-950 font-bold">
              <Bot className="w-5 h-5 text-vault-600" />
              <span>Grounded Assistant Analysis</span>
            </div>
            <span className="text-xs text-gray-400">
              Corpus: {response.authorized_docs_searched} authorized documents
            </span>
          </div>

          <div className="prose text-sm text-gray-800 leading-relaxed">
            {response.answer}
          </div>

          {response.insufficient_evidence && (
            <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg text-xs text-amber-800">
              Note: The available authorized documents provided limited explicit evidence for this query. The response is strictly bounded by authorized excerpts to avoid hallucination.
            </div>
          )}

          {/* Citations */}
          {response.cited_documents && response.cited_documents.length > 0 && (
            <div className="pt-4 border-t border-gray-100">
              <div className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">
                Referenced Document Evidence ({response.cited_documents.length})
              </div>
              <div className="space-y-2">
                {response.cited_documents.map((cite, idx) => (
                  <div
                    key={idx}
                    className="p-3 bg-gray-50 border border-gray-200 rounded-lg flex items-start justify-between text-xs"
                  >
                    <div className="space-y-1">
                      <div className="font-semibold text-vault-950 flex items-center space-x-1.5">
                        <FileText className="w-3.5 h-3.5 text-vault-600" />
                        <span>{cite.title}</span>
                      </div>
                      <p className="text-gray-600 font-mono text-[11px] line-clamp-2">
                        "{cite.chunk_preview}"
                      </p>
                    </div>
                    <span className="ml-4 px-2 py-0.5 bg-blue-50 text-blue-700 font-bold rounded">
                      {(cite.similarity_score * 100).toFixed(0)}% match
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
