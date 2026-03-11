/**
 * API client for the research agent backend.
 *
 * All backend calls go through this module. This gives us one place
 * to handle errors, add auth headers later, or swap the base URL.
 */

import {
  FeedbackRequest,
  MemoListItem,
  MemoRecord,
  MemoResponse,
} from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE}${path}`;
  const res = await fetch(url, {
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
    ...options,
  });

  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      detail = body.detail || detail;
    } catch {
      // response wasn't JSON, use status text
    }
    throw new ApiError(detail, res.status);
  }

  return res.json();
}

/** Generate a new investment memo */
export async function generateMemo(
  query: string,
  context?: string
): Promise<MemoResponse> {
  return request<MemoResponse>("/api/memos", {
    method: "POST",
    body: JSON.stringify({ query, context: context || null }),
  });
}

/** Get a specific memo by ID */
export async function getMemo(id: string): Promise<MemoRecord> {
  return request<MemoRecord>(`/api/memos/${id}`);
}

/** List recent memos */
export async function listMemos(
  limit = 50,
  offset = 0
): Promise<MemoListItem[]> {
  return request<MemoListItem[]>(
    `/api/memos?limit=${limit}&offset=${offset}`
  );
}

/** Submit feedback on a memo */
export async function submitFeedback(
  memoId: string,
  feedback: FeedbackRequest
): Promise<MemoRecord> {
  return request<MemoRecord>(`/api/memos/${memoId}/feedback`, {
    method: "POST",
    body: JSON.stringify(feedback),
  });
}
