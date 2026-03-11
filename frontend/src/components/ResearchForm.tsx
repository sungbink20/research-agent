"use client";

import { useState } from "react";

interface ResearchFormProps {
  onSubmit: (query: string, context?: string) => void;
  isLoading: boolean;
}

/**
 * The main input form for kicking off research.
 *
 * Intentionally simple: a text input for the company/protocol name
 * and an optional textarea for additional context. The context field
 * is collapsed by default to keep the UI clean for the common case.
 */
export default function ResearchForm({
  onSubmit,
  isLoading,
}: ResearchFormProps) {
  const [query, setQuery] = useState("");
  const [context, setContext] = useState("");
  const [showContext, setShowContext] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;
    onSubmit(query.trim(), context.trim() || undefined);
  };

  return (
    <form onSubmit={handleSubmit} className="w-full max-w-2xl mx-auto">
      <div className="space-y-4">
        <div>
          <label
            htmlFor="query"
            className="block text-sm font-medium text-zinc-300 mb-2"
          >
            Company or protocol to research
          </label>
          <input
            id="query"
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="e.g., Stripe, Uniswap, Anthropic, https://example.com"
            className="w-full px-4 py-3 bg-zinc-800 border border-zinc-700 rounded-lg text-white placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            disabled={isLoading}
            autoFocus
          />
        </div>

        {!showContext && (
          <button
            type="button"
            onClick={() => setShowContext(true)}
            className="text-sm text-zinc-400 hover:text-zinc-300 transition-colors"
          >
            + Add context (optional)
          </button>
        )}

        {showContext && (
          <div>
            <label
              htmlFor="context"
              className="block text-sm font-medium text-zinc-300 mb-2"
            >
              Additional context
            </label>
            <textarea
              id="context"
              value={context}
              onChange={(e) => setContext(e.target.value)}
              placeholder="e.g., Focus on their DeFi lending product, compare with Aave, interested in regulatory risk..."
              className="w-full px-4 py-3 bg-zinc-800 border border-zinc-700 rounded-lg text-white placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-y"
              rows={3}
              disabled={isLoading}
            />
          </div>
        )}

        <button
          type="submit"
          disabled={isLoading || !query.trim()}
          className="w-full py-3 px-6 bg-blue-600 hover:bg-blue-700 disabled:bg-zinc-700 disabled:text-zinc-500 text-white font-medium rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 focus:ring-offset-zinc-900"
        >
          {isLoading ? (
            <span className="flex items-center justify-center gap-2">
              <svg
                className="animate-spin h-5 w-5"
                viewBox="0 0 24 24"
                fill="none"
              >
                <circle
                  className="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  strokeWidth="4"
                />
                <path
                  className="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
                />
              </svg>
              Researching... (this takes 15-30 seconds)
            </span>
          ) : (
            "Generate Investment Memo"
          )}
        </button>
      </div>
    </form>
  );
}
