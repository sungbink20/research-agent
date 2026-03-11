"use client";

import { useState, useCallback } from "react";
import ResearchForm from "@/components/ResearchForm";
import MemoDisplay from "@/components/MemoDisplay";
import FeedbackForm from "@/components/FeedbackForm";
import MemoHistory from "@/components/MemoHistory";
import { generateMemo, getMemo } from "@/lib/api";
import { InvestmentMemo } from "@/lib/types";

/**
 * Main page of the research agent.
 *
 * Layout: single-page app with the form at top, memo below, and
 * history in a collapsible sidebar. No routing needed for MVP --
 * everything lives on one page for speed.
 *
 * State machine:
 *  idle -> loading -> (success | error)
 *  success: shows memo + feedback form
 *  error: shows error message + retry
 */

type AppState =
  | { status: "idle" }
  | { status: "loading"; query: string }
  | { status: "success"; memoId: string; memo: InvestmentMemo }
  | { status: "error"; message: string; query: string };

export default function Home() {
  const [state, setState] = useState<AppState>({ status: "idle" });
  const [refreshHistory, setRefreshHistory] = useState(0);
  const [showHistory, setShowHistory] = useState(false);

  const handleSubmit = useCallback(
    async (query: string, context?: string) => {
      setState({ status: "loading", query });

      try {
        const response = await generateMemo(query, context);
        setState({
          status: "success",
          memoId: response.id,
          memo: response.memo,
        });
        // Trigger history refresh so the new memo appears
        setRefreshHistory((n) => n + 1);
      } catch (err) {
        setState({
          status: "error",
          message:
            err instanceof Error ? err.message : "An unexpected error occurred",
          query,
        });
      }
    },
    []
  );

  const handleSelectMemo = useCallback(async (id: string) => {
    setState({ status: "loading", query: "Loading..." });
    try {
      const record = await getMemo(id);
      setState({
        status: "success",
        memoId: record.id,
        memo: record.memo,
      });
    } catch (err) {
      setState({
        status: "error",
        message:
          err instanceof Error ? err.message : "Failed to load memo",
        query: "",
      });
    }
  }, []);

  return (
    <div className="min-h-screen bg-zinc-950 text-white">
      {/* Top bar */}
      <header className="border-b border-zinc-800">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div>
            <h1 className="text-lg font-semibold text-white">
              Research Agent
            </h1>
            <p className="text-xs text-zinc-500">
              First-pass investment memo generator
            </p>
          </div>
          <button
            onClick={() => setShowHistory(!showHistory)}
            className="text-sm text-zinc-400 hover:text-white transition-colors px-3 py-1.5 rounded-lg hover:bg-zinc-800"
          >
            {showHistory ? "Hide History" : "History"}
          </button>
        </div>
      </header>

      <div className="flex">
        {/* History sidebar */}
        {showHistory && (
          <aside className="w-80 border-r border-zinc-800 min-h-[calc(100vh-65px)] bg-zinc-900/50">
            <div className="p-4 border-b border-zinc-800">
              <h2 className="text-sm font-medium text-zinc-400">
                Recent Memos
              </h2>
            </div>
            <MemoHistory
              onSelectMemo={handleSelectMemo}
              refreshTrigger={refreshHistory}
            />
          </aside>
        )}

        {/* Main content */}
        <main className="flex-1 px-6 py-12">
          {/* Always show the form */}
          <div className="mb-12">
            <ResearchForm
              onSubmit={handleSubmit}
              isLoading={state.status === "loading"}
            />
          </div>

          {/* Loading state */}
          {state.status === "loading" && (
            <div className="max-w-2xl mx-auto text-center py-16">
              <div className="animate-pulse space-y-4">
                <div className="h-4 bg-zinc-800 rounded w-3/4 mx-auto" />
                <div className="h-4 bg-zinc-800 rounded w-1/2 mx-auto" />
                <div className="h-4 bg-zinc-800 rounded w-2/3 mx-auto" />
              </div>
              <p className="text-zinc-500 text-sm mt-8">
                Researching{" "}
                <span className="text-zinc-300">{state.query}</span>...
              </p>
              <p className="text-zinc-600 text-xs mt-2">
                The AI is analyzing public information and generating a
                structured memo. This typically takes 15-30 seconds.
              </p>
            </div>
          )}

          {/* Error state */}
          {state.status === "error" && (
            <div className="max-w-2xl mx-auto">
              <div className="bg-red-900/20 border border-red-800/50 rounded-lg p-6">
                <h3 className="text-red-400 font-medium mb-2">
                  Research Failed
                </h3>
                <p className="text-red-300/70 text-sm">{state.message}</p>
                <button
                  onClick={() => handleSubmit(state.query)}
                  className="mt-4 px-4 py-2 bg-red-800/30 hover:bg-red-800/50 text-red-300 text-sm rounded-lg transition-colors"
                >
                  Retry
                </button>
              </div>
            </div>
          )}

          {/* Success state: memo + feedback */}
          {state.status === "success" && (
            <div className="space-y-8">
              <MemoDisplay memo={state.memo} memoId={state.memoId} />
              <div className="max-w-4xl mx-auto">
                <FeedbackForm memoId={state.memoId} />
              </div>
            </div>
          )}

          {/* Idle state: instructions */}
          {state.status === "idle" && (
            <div className="max-w-2xl mx-auto text-center py-16">
              <p className="text-zinc-500">
                Enter a company name, protocol, or URL above to generate a
                first-pass investment memo.
              </p>
              <div className="mt-8 grid grid-cols-2 md:grid-cols-4 gap-3">
                {["Stripe", "Uniswap", "Anthropic", "Solana"].map(
                  (example) => (
                    <button
                      key={example}
                      onClick={() => handleSubmit(example)}
                      className="px-3 py-2 bg-zinc-800/50 border border-zinc-700/50 rounded-lg text-sm text-zinc-400 hover:text-white hover:border-zinc-600 transition-colors"
                    >
                      {example}
                    </button>
                  )
                )}
              </div>
              <p className="text-zinc-600 text-xs mt-4">
                Click an example to try it
              </p>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
