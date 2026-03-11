"use client";

import { useEffect, useState } from "react";
import { listMemos } from "@/lib/api";
import { MemoListItem } from "@/lib/types";

interface MemoHistoryProps {
  onSelectMemo: (id: string) => void;
  refreshTrigger?: number; // increment to force refresh
}

/**
 * Sidebar/section showing recent memos for quick navigation.
 * Lightweight list view -- click to load the full memo.
 */
export default function MemoHistory({
  onSelectMemo,
  refreshTrigger,
}: MemoHistoryProps) {
  const [memos, setMemos] = useState<MemoListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchMemos = async () => {
      setLoading(true);
      try {
        const data = await listMemos(20);
        setMemos(data);
        setError(null);
      } catch (err) {
        setError("Could not load history");
        console.error("Failed to load memo history:", err);
      } finally {
        setLoading(false);
      }
    };
    fetchMemos();
  }, [refreshTrigger]);

  if (loading) {
    return (
      <div className="text-zinc-500 text-sm p-4">Loading history...</div>
    );
  }

  if (error) {
    return <div className="text-red-400 text-sm p-4">{error}</div>;
  }

  if (memos.length === 0) {
    return (
      <div className="text-zinc-500 text-sm p-4">
        No memos yet. Generate your first one above.
      </div>
    );
  }

  return (
    <div className="space-y-1">
      {memos.map((memo) => (
        <button
          key={memo.id}
          onClick={() => onSelectMemo(memo.id)}
          className="w-full text-left px-4 py-3 rounded-lg hover:bg-zinc-800 transition-colors group"
        >
          <div className="flex items-center justify-between">
            <span className="text-sm text-white font-medium group-hover:text-blue-400 transition-colors truncate">
              {memo.company_name}
            </span>
            <span className="text-xs text-zinc-600 flex-shrink-0 ml-2">
              {new Date(memo.created_at).toLocaleDateString()}
            </span>
          </div>
          <div className="flex items-center gap-2 mt-1">
            <span className="text-xs text-zinc-500 truncate">
              {memo.query}
            </span>
            <span className="text-xs px-1.5 py-0.5 bg-zinc-800 text-zinc-500 rounded flex-shrink-0">
              {memo.category}
            </span>
          </div>
        </button>
      ))}
    </div>
  );
}
