"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { UploadCloud, FileText, Trash2, Search, CheckCircle, Clock, AlertCircle, RefreshCw } from "lucide-react";
import { toast } from "sonner";
import apiClient from "@/lib/api";

interface KnowledgeDoc {
  id: string;
  title: string;
  file_name: string;
  file_type: string;
  file_size_bytes: number;
  status: "pending" | "processing" | "indexed" | "failed";
  chunk_count: number;
  tags?: string[];
  created_at: string;
}

interface RetrievedChunk {
  chunk_id: string;
  content: string;
  document_title: string;
  similarity_score: number;
}

export default function KnowledgeBasePage() {
  const qc = useQueryClient();
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState("");
  const [tags, setTags] = useState("");
  const [isUploading, setIsUploading] = useState(false);

  // Search playground
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<RetrievedChunk[] | null>(null);
  const [isSearching, setIsSearching] = useState(false);

  // Fetch docs
  const { data, isLoading } = useQuery<{ items: KnowledgeDoc[]; total: number }>({
    queryKey: ["knowledge-documents"],
    queryFn: () => apiClient.get("/knowledge").then((r) => r.data),
    refetchInterval: 10_000,
  });

  // Upload mutation
  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) {
      toast.error("Please select a file to upload");
      return;
    }

    setIsUploading(true);
    const formData = new FormData();
    formData.append("file", file);
    if (title) formData.append("title", title);
    if (tags) formData.append("tags", tags);

    try {
      await apiClient.post("/knowledge/upload", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      toast.success("Document uploaded and indexing started!");
      setFile(null);
      setTitle("");
      setTags("");
      qc.invalidateQueries({ queryKey: ["knowledge-documents"] });
    } catch (err: any) {
      const msg = err.response?.data?.error?.message ?? "Upload failed";
      toast.error(msg);
    } finally {
      setIsUploading(false);
    }
  };

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: (id: string) => apiClient.delete(`/knowledge/${id}`),
    onSuccess: () => {
      toast.success("Document removed");
      qc.invalidateQueries({ queryKey: ["knowledge-documents"] });
    },
    onError: () => toast.error("Failed to delete document"),
  });

  // Query test
  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchQuery.trim()) return;

    setIsSearching(true);
    try {
      const res = await apiClient.post("/knowledge/query", {
        query: searchQuery,
        top_k: 4,
        min_similarity: 0.3,
      });
      setSearchResults(res.data.results);
    } catch {
      toast.error("Search query failed");
    } finally {
      setIsSearching(false);
    }
  };

  const getStatusBadge = (status: KnowledgeDoc["status"]) => {
    switch (status) {
      case "indexed":
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-400">
            <CheckCircle className="w-3 h-3" /> Indexed
          </span>
        );
      case "processing":
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400">
            <RefreshCw className="w-3 h-3 animate-spin" /> Processing
          </span>
        );
      case "failed":
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400">
            <AlertCircle className="w-3 h-3" /> Failed
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-300">
            <Clock className="w-3 h-3" /> Pending
          </span>
        );
    }
  };

  return (
    <div className="space-y-8 animate-fade-in">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Knowledge Base & RAG Ingestion</h1>
        <p className="text-gray-500 dark:text-gray-400 text-sm mt-1">
          Upload documents to chunk, embed, and index into ChromaDB for high-accuracy AI responses.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Upload Card */}
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6">
          <h2 className="text-base font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
            <UploadCloud className="w-5 h-5 text-brand-600" /> Upload Document
          </h2>
          <form onSubmit={handleUpload} className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                File (PDF, TXT, MD, DOCX)
              </label>
              <input
                type="file"
                accept=".pdf,.txt,.md,.docx"
                onChange={(e) => setFile(e.target.files?.[0] || null)}
                className="w-full text-xs file:mr-3 file:py-2 file:px-3 file:rounded-md file:border-0 file:text-xs file:font-semibold file:bg-brand-50 file:text-brand-700 hover:file:bg-brand-100 border border-gray-300 dark:border-gray-600 rounded-lg p-2"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                Display Title (optional)
              </label>
              <input
                type="text"
                placeholder="e.g. Return Policy & Billing FAQ"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 text-sm bg-transparent"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                Tags (comma separated)
              </label>
              <input
                type="text"
                placeholder="billing, policy, onboarding"
                value={tags}
                onChange={(e) => setTags(e.target.value)}
                className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 text-sm bg-transparent"
              />
            </div>

            <button
              type="submit"
              disabled={isUploading || !file}
              className="w-full py-2.5 px-4 bg-brand-600 hover:bg-brand-700 disabled:opacity-50 text-white font-medium text-sm rounded-lg transition"
            >
              {isUploading ? "Chunking & Embedding..." : "Upload & Ingest to RAG"}
            </button>
          </form>
        </div>

        {/* Documents Table */}
        <div className="lg:col-span-2 bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6 flex flex-col">
          <h2 className="text-base font-semibold text-gray-900 dark:text-white mb-4 flex items-center justify-between">
            <span>Ingested Documents ({data?.total ?? 0})</span>
            <button
              onClick={() => qc.invalidateQueries({ queryKey: ["knowledge-documents"] })}
              className="p-1 rounded text-gray-400 hover:text-gray-600 dark:hover:text-gray-200"
            >
              <RefreshCw className="w-4 h-4" />
            </button>
          </h2>

          <div className="flex-1 overflow-x-auto">
            {isLoading ? (
              <div className="py-12 text-center text-gray-400 text-sm">Loading documents...</div>
            ) : !data?.items.length ? (
              <div className="py-12 text-center text-gray-400 text-sm">
                No documents uploaded yet. Upload a document to start semantic retrieval.
              </div>
            ) : (
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-gray-200 dark:border-gray-700 text-xs text-gray-400 uppercase">
                    <th className="py-2.5 px-3">Title / File</th>
                    <th className="py-2.5 px-3">Chunks</th>
                    <th className="py-2.5 px-3">Status</th>
                    <th className="py-2.5 px-3 text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
                  {data.items.map((doc) => (
                    <tr key={doc.id} className="hover:bg-gray-50/50 dark:hover:bg-gray-700/50">
                      <td className="py-3 px-3">
                        <div className="font-medium text-gray-900 dark:text-white">{doc.title}</div>
                        <div className="text-xs text-gray-400 flex items-center gap-1.5 mt-0.5">
                          <FileText className="w-3.5 h-3.5" />
                          {doc.file_name} ({(doc.file_size_bytes / 1024).toFixed(1)} KB)
                        </div>
                      </td>
                      <td className="py-3 px-3 text-xs text-gray-600 dark:text-gray-300">
                        {doc.chunk_count} chunks
                      </td>
                      <td className="py-3 px-3">{getStatusBadge(doc.status)}</td>
                      <td className="py-3 px-3 text-right">
                        <button
                          onClick={() => deleteMutation.mutate(doc.id)}
                          className="p-1 text-gray-400 hover:text-red-500 rounded transition"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      </div>

      {/* RAG Retrieval Test Playground */}
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6">
        <h2 className="text-base font-semibold text-gray-900 dark:text-white mb-2 flex items-center gap-2">
          <Search className="w-5 h-5 text-brand-600" /> RAG Semantic Search Playground
        </h2>
        <p className="text-xs text-gray-500 dark:text-gray-400 mb-4">
          Test semantic retrieval against your organization's vector store in ChromaDB.
        </p>

        <form onSubmit={handleSearch} className="flex gap-3 mb-6">
          <input
            type="text"
            placeholder="Ask a question or enter keywords, e.g. 'What is the refund process for annual plans?'"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="flex-1 px-4 py-2.5 rounded-lg border border-gray-300 dark:border-gray-600 text-sm bg-transparent focus:outline-none focus:ring-2 focus:ring-brand-500"
          />
          <button
            type="submit"
            disabled={isSearching}
            className="px-5 py-2.5 bg-gray-900 text-white hover:bg-black dark:bg-brand-600 dark:hover:bg-brand-700 text-sm font-medium rounded-lg transition"
          >
            {isSearching ? "Retrieving..." : "Search Chunks"}
          </button>
        </form>

        {searchResults && (
          <div className="space-y-3">
            <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider">
              Retrieved Context Chunks ({searchResults.length})
            </h3>
            {searchResults.length === 0 ? (
              <p className="text-sm text-gray-400">No matching chunks met the similarity threshold.</p>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {searchResults.map((res) => (
                  <div
                    key={res.chunk_id}
                    className="p-4 rounded-lg bg-gray-50 dark:bg-gray-700/50 border border-gray-200 dark:border-gray-700 text-xs space-y-2"
                  >
                    <div className="flex items-center justify-between font-semibold text-gray-700 dark:text-gray-300">
                      <span>{res.document_title}</span>
                      <span className="text-brand-600 dark:text-brand-400 bg-brand-50 dark:bg-brand-900/40 px-2 py-0.5 rounded">
                        Score: {(res.similarity_score * 100).toFixed(1)}%
                      </span>
                    </div>
                    <p className="text-gray-600 dark:text-gray-400 whitespace-pre-wrap leading-relaxed">
                      {res.content}
                    </p>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
